# HuMo Lipsync Suppress

A ComfyUI custom node for suppressing lip-sync motion in HuMo audio embeddings with a simple boolean toggle, plus an automatic threshold switcher for intelligent suppression control.

## 🎯 Overview

This package provides two nodes for controlling lip-sync suppression in HuMo-generated character animations:

1. **HuMo Lipsync Suppress**: A one-click solution to reduce or eliminate lip/mouth movement. When enabled, it applies optimized preset band gains to the HuMo audio embeddings. When disabled, embeddings pass through unchanged.

2. **HuMo Audio Threshold Switcher**: Automatically enables suppression based on audio volume. Perfect for processing vocal stems that may contain silent segments or residual background noise - the suppressor activates automatically when audio is below a configurable RMS threshold.

## ✨ Features

- **🔘 Simple Boolean Toggle** - Enable/disable with a single checkbox
- **⚡ Zero Configuration** - Preset values optimized for lip-sync suppression
- **🎛️ Multi-Band Processing** - Targets 5 frequency bands from Whisper-derived features
- **🌊 Temporal Smoothing** - EMA filtering reduces flickering artifacts
- **🔌 Drop-in Replacement** - Compatible with existing HuMo workflows
- **🎚️ Automatic Threshold Switcher** - New node that automatically enables suppression based on audio RMS threshold

## 📦 Installation

### Method 1: Git Clone

1. Navigate to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes/
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/ckinpdx/HuMoLipsyncSuppress.git
   ```

3. Restart ComfyUI

### Method 2: Direct Download

1. Download the repository as ZIP
2. Extract to `ComfyUI/custom_nodes/HuMoLipsyncSuppress/`
3. Ensure the folder structure is:
   ```
   ComfyUI/custom_nodes/HuMoLipsyncSuppress/
   ├── __init__.py
   ├── nodes.py
   └── README.md
   ```
4. Restart ComfyUI

## 🚀 Usage

1. In ComfyUI, locate the node under:
   ```
   Add Node → HuMo Audio/Motion → HuMo Lipsync Suppress
   ```

2. Connect your workflow:
   ```
   [HuMo Embeds] → [HuMo Lipsync Suppress] → [WanVideoSampler]
                                      ↓
                                  enabled: ✓
   ```

3. Toggle the `enabled` parameter:
   - **✓ Enabled (True)**: Applies lip-sync suppression
   - **☐ Disabled (False)**: Passes embeddings unchanged

### Using the Audio Threshold Switcher

The **HuMo Audio Threshold Switcher** node automatically controls the suppressor based on audio volume:

1. Locate the node under:
   ```
   Add Node → HuMo Audio/Motion → HuMo Audio Threshold Switcher
   ```

2. Connect your workflow:
   ```
   [Vocal Stem Audio] → [HuMo Audio Threshold Switcher] → [HuMo Lipsync Suppress]
                              ↓                                    ↓
                         threshold: 0.01                      enabled: (auto)
                         invert: False
   ```

3. Configure the parameters:
   - **threshold**: RMS volume threshold (default: 0.01). Audio below this value is considered silent.
   - **invert**: If enabled, flips the logic to enable suppressor when audio is LOUD instead of silent.

4. How it works:
   - When audio RMS < threshold (silent): Outputs `True` → Enables suppressor
   - When audio RMS >= threshold (audio present): Outputs `False` → Disables suppressor
   - Perfect for vocal stems that may contain silent segments or residual background noise

## ⚙️ Technical Details

### Input/Output

- **Input**: `WANVIDIMAGE_EMBEDS` (containing `humo_audio_emb` key)
- **Output**: `WANVIDIMAGE_EMBEDS` (modified or passed through)

### Expected Embedding Shape

```
[T, 5, 1280]
```
- `T`: Number of time frames
- `5`: Frequency bands (Whisper-derived)
- `1280`: Embedding dimension

### Preset Band Gains

The node applies these fixed values when enabled:

| Band | Frequency Range | Gain | Effect |
|------|----------------|------|--------|
| 0 | Shallow edges/onsets | 4.00 | Boost transients |
| 1 | Short-term rhythm | 4.00 | Boost rhythm |
| 2 | Phrase patterns | 0.50 | Moderate reduction |
| 3 | Long-range cadence | 0.01 | Heavy suppression |
| 4 | Top semantic | 0.01 | Heavy suppression |

### Additional Processing

- **EMA Beta**: 0.90 (temporal smoothing)
- **Alpha Mix**: 1.00 (full blend with edited signal)
- **RMS Preservation**: False
- **Global Gain**: 1.00
- **Clamp Std**: 0.00 (disabled)

## 🎨 Use Cases

- **Stylized Animation**: Create non-realistic character reactions
- **Audio-Reactive Motion**: Keep body movement while suppressing lips
- **Artistic Control**: Selective lip-sync suppression in workflows
- **Automatic Suppression**: Use the threshold switcher to automatically enable suppression during silent segments in vocal stems
- **Vocal Stem Processing**: Handle stems separated with tools like MelBandFormer that may contain glitches or background vocal remnants

## 🔧 Requirements

- ComfyUI
- PyTorch
- HuMo audio embeddings with proper format

## 📝 How It Works

### HuMo Lipsync Suppress Node

1. **Band Separation**: HuMo audio embeddings contain 5 frequency bands derived from Whisper features
2. **Gain Application**: Bands 3-4 (containing primary lip-sync cues) are heavily suppressed (0.01x)
3. **Transient Boost**: Bands 0-1 are amplified (4.00x) to maintain motion energy
4. **Temporal Smoothing**: EMA filter (β=0.90) reduces frame-to-frame flickering
5. **Full Blend**: Edited signal completely replaces original (α=1.00)

### HuMo Audio Threshold Switcher Node

1. **Audio Input**: Accepts audio in various formats (torch tensors, numpy arrays, tuples/lists)
2. **RMS Calculation**: Computes Root Mean Square amplitude of the entire audio clip
3. **Threshold Comparison**: Compares RMS value against the configured threshold
4. **Boolean Output**: Returns `True` (enable suppressor) when audio is silent (RMS < threshold), `False` otherwise
5. **Format Flexibility**: Automatically handles different audio input formats commonly used in ComfyUI workflows

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is a derivative work based on the HuMo Audio Band Editor. Please ensure compliance with the original project's license terms.

## 🙏 Acknowledgments

- Based on the [HuMo Audio Band Editor]
- Inspired by the HuMo (Human Motion) project
- Built for the ComfyUI community

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/HuMoLipsyncSuppress/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/HuMoLipsyncSuppress/discussions)

## 🔗 Related Projects

- [HuMo](https://github.com/link-to-humo) - Human Motion generation
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Powerful node-based UI
- [Wanvid](https://github.com/link-to-wanvid) - Video generation framework

---

**⭐ If you find this node useful, please consider giving it a star!**
