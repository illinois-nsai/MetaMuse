# MetaMuse: Algorithm Generation via Creative Ideation
[![arXiv](https://img.shields.io/badge/arXiv-2510.03851-00ff00.svg)](https://arxiv.org/abs/2510.03851)

🎉 **Accepted to ICLR 2026!**

**Purpose:** drive algorithm *invention* rather than imitation by reducing availability bias with a structured creative workflow.

**Impact on real system workloads (global cloud provider):**
- Cache replacement: up to 35.76% fewer cache misses
- Online bin packing: up to 30.93% reduction in bin usage
- Solution diversity: up to ~1.8× more diverse than baseline LLM approaches

**Core ideas:**

- Performance-grounded diversity: measure diversity using real performance impact.
- External stimuli steering: use curated keywords to trigger creative reasoning.
- Waypoint reasoning: synthesize executable solutions through structured checkpoints.

## Setup

### 1) Create a conda environment

```bash
conda create -n metamuse python=3.8
conda activate metamuse
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

Notes: `openbox` is installed from PyPI by default. For source install, see https://github.com/PKU-DAIR/open-box.

### 3) Configure LLM credentials

Create `src/.env` with:
```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_MODEL_GPT=...
```

Optional alternative providers:
```
AZURE_LLAMA33_ENDPOINT=...
AZURE_LLAMA33_API_VERSION=...
AZURE_LLAMA33_API_KEY=...
AZURE_LLAMA33_MODEL=...

AZURE_DEEPSEEKV3_ENDPOINT=...
AZURE_DEEPSEEKV3_API_VERSION=...
AZURE_DEEPSEEKV3_API_KEY=...
AZURE_DEEPSEEKV3_MODEL=...
```

## Run

Example (BPP Online):
```bash
python run.py \
  --algo rsdict \
  --problem bpp_online \
  --trace_folder /path/to/trace_folder \
  --code_folder /path/to/code_out \
  --tot_llm_call_num 50 \
  --hint_word_count 5
```

Example (Cache):
```bash
python run.py \
  --algo rsdict_sf \
  --problem cache \
  --trace_folder /path/to/trace_folder \
  --code_folder /path/to/code_out \
  --capacity 10000 \
  --tot_llm_call_num 50 \
  --hint_word_count 5 \
  --consider_obj_size
```

All log/code output directories are created automatically when the run starts.

## Cite

```bibtex
@article{ma2025algorithm,
  title={Algorithm Generation via Creative Ideation},
  author={Ma, Ruiying and Liang, Chieh-Jan Mike and Gao, Yanjie and Yan, Francis Y.},
  journal={arXiv preprint arXiv:2510.03851},
  year={2025}
}
```
