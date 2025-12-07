import torch
import numpy as np

class HuMoLipsyncSuppress:
    """
    Simplified HuMo audio editor that suppresses lip-sync on boolean trigger.
    When enabled=True, applies preset band gains to reduce mouth movement.
    When enabled=False, passes through unchanged.
    
    Preset settings (from reference image):
      - gain_b0: 4.00 (shallow edges/onsets)
      - gain_b1: 4.00 (short-term rhythm)
      - gain_b2: 0.50 (phrase patterns)
      - gain_b3: 0.01 (long-range cadence)
      - gain_b4: 0.01 (top semantic)
      - ema_beta: 0.90
      - preserve_rms: False
      - alpha_mix: 1.00
      - global_gain: 1.00
      - clamp_std: 0.00 (disabled)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_embeds": ("WANVIDIMAGE_EMBEDS",),
                "enabled": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Enable lipsync suppression (apply preset gains)"
                }),
            }
        }

    RETURN_TYPES = ("WANVIDIMAGE_EMBEDS",)
    RETURN_NAMES = ("image_embeds",)
    FUNCTION = "apply"
    CATEGORY = "HuMo Audio/Motion"
    DESCRIPTION = "Apply preset band gains to suppress lip-sync motion (boolean trigger)."

    # Preset values from reference image
    PRESET_GAINS = [4.00, 4.00, 0.50, 0.01, 0.01]
    PRESET_EMA_BETA = 0.90
    PRESET_PRESERVE_RMS = False
    PRESET_ALPHA_MIX = 1.00
    PRESET_GLOBAL_GAIN = 1.00
    PRESET_CLAMP_STD = 0.00

    def _rms(self, x, eps=1e-6):
        """Per-frame, per-band RMS (keep channel dim)"""
        return x.pow(2).mean(dim=-1, keepdim=True).sqrt().clamp_min(eps)

    def apply(self, image_embeds, enabled):
        # If disabled, return unchanged
        if not enabled:
            return (image_embeds,)

        # Shallow copy dict to avoid side-effects
        embeds = dict(image_embeds)
        key = "humo_audio_emb"
        
        if key not in embeds:
            raise ValueError("Missing key 'humo_audio_emb' in WANVIDIMAGE_EMBEDS")

        x = embeds[key]  # [T, 5, 1280]
        if x.ndim != 3 or x.shape[1] != 5:
            raise ValueError(f"humo_audio_emb expected shape [T,5,C], got {tuple(x.shape)}")

        device = x.device
        dtype = x.dtype
        x_orig = x

        # Apply preset per-band gains
        gains = torch.tensor(self.PRESET_GAINS, device=device, dtype=dtype).view(1, 5, 1)

        # Temporal EMA smoothing
        if x.shape[0] > 1 and self.PRESET_EMA_BETA > 0.0:
            s = x[0].clone()
            out_seq = [s]
            beta = torch.tensor(self.PRESET_EMA_BETA, device=device, dtype=dtype)
            one_m = (1.0 - beta).to(dtype)
            for t in range(1, x.shape[0]):
                s = beta * s + one_m * x[t]
                out_seq.append(s)
            x_smooth = torch.stack(out_seq, dim=0)
        else:
            x_smooth = x

        # Apply gains
        x_edit = x_smooth * gains

        # RMS preservation (disabled in preset)
        if self.PRESET_PRESERVE_RMS:
            rms_orig = self._rms(x_orig)
            rms_edit = self._rms(x_edit)
            x_edit = x_edit * (rms_orig / rms_edit)

        # Residual blend (alpha=1.0 means full edit)
        alpha = torch.tensor(self.PRESET_ALPHA_MIX, device=device, dtype=dtype)
        x_mixed = (1.0 - alpha) * x_orig + alpha * x_edit
        
        # Global gain
        if self.PRESET_GLOBAL_GAIN != 1.0:
            x_mixed = x_mixed * self.PRESET_GLOBAL_GAIN

        # Clamp (disabled in preset)
        if self.PRESET_CLAMP_STD > 0.0:
            mean = x_mixed.mean()
            std = x_mixed.std().clamp_min(1e-6)
            lo = mean - self.PRESET_CLAMP_STD * std
            hi = mean + self.PRESET_CLAMP_STD * std
            x_mixed = x_mixed.clamp(lo, hi)

        embeds[key] = x_mixed
        return (embeds,)


class HuMoAudioThresholdSwitcher:
    """
    Audio threshold switcher that analyzes audio input and outputs a boolean signal
    based on RMS volume threshold. When audio is silent (below threshold), outputs
    True to enable the lipsync suppressor. When audio is present (above threshold),
    outputs False to disable the suppressor.
    
    Useful for automatically enabling suppression when processing vocal stems that
    may contain silent segments or residual background noise.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("*", {
                    "tooltip": "Audio input (numpy array, torch tensor, or list/tuple containing audio data)"
                }),
                "threshold": ("FLOAT", {
                    "default": 0.01,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001,
                    "tooltip": "RMS volume threshold. Audio below this value is considered silent."
                }),
                "invert": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Invert the logic: True = enable suppressor when audio is LOUD (above threshold)"
                }),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("enabled",)
    FUNCTION = "analyze"
    CATEGORY = "HuMo Audio/Motion"
    DESCRIPTION = "Analyze audio RMS and output boolean to control lipsync suppressor based on volume threshold."

    def _convert_to_tensor(self, audio):
        """Convert various audio formats to a torch tensor."""
        if isinstance(audio, torch.Tensor):
            return audio.float()
        elif isinstance(audio, np.ndarray):
            return torch.from_numpy(audio).float()
        elif isinstance(audio, (list, tuple)):
            # Handle tuple/list formats like (sample_rate, audio_data)
            if len(audio) == 2 and isinstance(audio[1], (np.ndarray, torch.Tensor, list)):
                # Assume format is (sample_rate, audio_data)
                audio_data = audio[1]
                if isinstance(audio_data, torch.Tensor):
                    return audio_data.float()
                elif isinstance(audio_data, np.ndarray):
                    return torch.from_numpy(audio_data).float()
                else:
                    return torch.tensor(audio_data, dtype=torch.float32)
            else:
                # Assume it's a flat list of audio samples
                return torch.tensor(audio, dtype=torch.float32)
        else:
            # Try to convert to tensor directly
            try:
                return torch.tensor(audio, dtype=torch.float32)
            except:
                raise ValueError(f"Unsupported audio format: {type(audio)}")

    def _calculate_rms(self, audio_tensor):
        """Calculate RMS (Root Mean Square) amplitude of audio."""
        # Flatten the tensor to get all samples
        audio_flat = audio_tensor.flatten()
        
        # Calculate RMS: sqrt(mean(samples^2))
        rms = torch.sqrt(torch.mean(audio_flat ** 2))
        
        # Handle edge case of empty or all-zero audio
        if torch.isnan(rms) or torch.isinf(rms):
            return 0.0
        
        return rms.item()

    def analyze(self, audio, threshold, invert):
        """
        Analyze audio RMS and determine if suppressor should be enabled.
        
        Args:
            audio: Audio input in various formats (numpy array, torch tensor, etc.)
            threshold: RMS threshold value (0.0 to 1.0)
            invert: If True, invert the logic
        
        Returns:
            enabled (bool): True to enable suppressor, False to disable
        """
        # Convert audio to tensor
        audio_tensor = self._convert_to_tensor(audio)
        
        # Calculate RMS
        rms = self._calculate_rms(audio_tensor)
        
        # Determine if audio is silent (below threshold)
        is_silent = rms < threshold
        
        # Default logic: enable suppressor when silent
        if invert:
            # Inverted: enable suppressor when audio is LOUD (above threshold)
            enabled = not is_silent
        else:
            # Normal: enable suppressor when audio is SILENT (below threshold)
            enabled = is_silent
        
        return (enabled,)


NODE_CLASS_MAPPINGS = {
    "HuMoLipsyncSuppress": HuMoLipsyncSuppress,
    "HuMoAudioThresholdSwitcher": HuMoAudioThresholdSwitcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HuMoLipsyncSuppress": "HuMo Lipsync Suppress",
    "HuMoAudioThresholdSwitcher": "HuMo Audio Threshold Switcher",
}
