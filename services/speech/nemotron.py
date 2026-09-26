"""Nemotron diarization with bounded PCM reads and one persistent speaker cache."""

from pathlib import Path

from services.api.pcm import Reader
from .baselines import verified_manifest


class SpeakerTurns:
    def __init__(self, source_samples, hop=160, speakers=8):
        self.source_samples, self.hop, self.speakers = source_samples, hop, speakers
        self.frame = 0
        self.active = {}
        self.turns = []

    def feed(self, active_frames):
        for frame in active_frames:
            if len(frame) != self.speakers:
                raise ValueError('speaker_channel_count_changed')
            start = self.frame * self.hop
            if start >= self.source_samples:
                break
            for speaker, active in enumerate(frame):
                if active and speaker not in self.active:
                    self.active[speaker] = start
                elif not active and speaker in self.active:
                    self.close(speaker,start)
            self.frame += 1

    def close(self, speaker, end):
        start = self.active.pop(speaker)
        if end > start:
            self.turns.append({'start_sample':start,'end_sample':end,'cluster':f'SPEAKER_{speaker:02d}'})

    def finish(self):
        end = min(self.frame*self.hop,self.source_samples)
        for speaker in list(self.active):
            self.close(speaker,end)
        return sorted(self.turns,key=lambda turn:(turn['start_sample'],turn['cluster']))


class NemotronEngine:
    def __init__(self, device='cuda:0', mode='offline_context'):
        self.manifest, path = verified_manifest('speech-models.lock.json','nemotron_diarization','nemotron-diarization')
        import torch
        from transformers import AutoModelForAudioFrameClassification, AutoProcessor

        self.torch, self.device = torch, device
        self.processor = AutoProcessor.from_pretrained(path,local_files_only=True,trust_remote_code=False)
        self.model = AutoModelForAudioFrameClassification.from_pretrained(
            path,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,
            attn_implementation='sdpa').to(device).eval()
        self.mode = mode
        if mode == 'offline_context':
            self.processor.streaming_modes = {**self.processor.streaming_modes,
                'offline_context':(self.model.config.chunk_length,self.model.config.chunk_right_context)}
        self.processor.set_streaming_mode(mode)

    def blocks(self, path):
        import numpy as np
        from transformers.models.nemotron3_diarization.modeling_nemotron3_diarization import Nemotron3DiarizationSpeakerCache

        offline = {'fifo_length':self.model.config.fifo_length,
                   'speaker_cache_update_period':self.model.config.speaker_cache_update_period} if self.mode == 'offline_context' else {}
        cache = Nemotron3DiarizationSpeakerCache(self.model.config.streaming_config,**offline)
        processor = self.processor
        frame, mel_cursor, start, first = 0, 0, 0, True
        with Reader(Path(path)) as reader:
            if reader.getframerate() != 16000:
                raise ValueError('nemotron_requires_canonical_16khz')
            samples = reader.getnframes()
            while start < samples:
                size = processor.num_samples_first_audio_chunk if first else processor.num_samples_per_audio_chunk
                end = min(start+size,samples)
                reader.setpos(start)
                audio = np.frombuffer(reader.readframes(end-start),dtype='<i2').astype(np.float32)/32768.0
                last = end == samples
                # Later uncentered STFT chunks need the right-hand padding that
                # a whole-file centered STFT supplies at EOF. Never score padding.
                padding = processor.feature_extractor.n_fft//2 if last and not first else 0
                if padding:
                    audio = np.pad(audio,(0,padding))
                inputs = processor(audio,sampling_rate=16000,is_streaming=True,
                    is_first_audio_chunk=first,is_last_audio_chunk=last).to(self.device,self.torch.float32)
                with self.torch.inference_mode():
                    output = self.model(**inputs,speaker_cache=cache)
                cache = output.speaker_cache
                logits = output.logits[0].float().cpu()
                usable = min(logits.shape[0],samples//160-frame)
                logits = logits[:usable]
                yield {'start_frame':frame,'source_samples':samples,'probabilities':logits.sigmoid().numpy(),
                       'audio_start':start,'audio_end':end,'last':last,'eof_padding_samples':padding}
                frame += usable
                if last:
                    break
                mel_cursor += processor.num_mel_frames_per_step
                start = processor.audio_chunk_start(mel_cursor)
                first = False
