# **MetaMuse: Algorithm Generation via Creative Ideation**
[![arXiv](https://img.shields.io/badge/arXiv-2510.03851-00ff00.svg)](https://arxiv.org/abs/2510.03851)

Work done by researchers **@ UC Berkeley · Microsoft Research · UIUC**


## 📢 News

**🎉 Accepted to ICLR 2026**!! 
This work marks a significant step in enabling AI systems to *invent novel algorithms*, not just rehash existing heuristics.


## 💡 Why MetaMuse?

LLMs are amazing at mimicking known designs, but they struggle to *invent* fresh algorithmic strategies due to an inherent *availability bias*—they tend to output what they’ve seen before rather than what *should* be invented.

**MetaMuse** addresses this issue by introducing a structured *creative ideation workflow* that enables LLMs to take *discontinuous leaps* in solution space.


## 📈 Applications on Real Systems

Evaluated on real-world system workloads from a global cloud provider:

🔥 **Cache Replacement: Up to 35.76% fewer cache misses**


🔥 **Online Bin Packing: Up to 30.93% reduction in bin usage**


📌 **MetaMuse also *generates more diverse solutions* — up to ~1.8× more than baseline LLM approaches** — making it not just effective but *creatively explorative*.

## 🧩 Core Mechanism

MetaMuse is built on **three  principles**:

📊 **Performance-grounded diversity** — measure diversity in terms of *real performance impact*, not superficial textual differences.

🌟 **External stimuli steering** — uses curated keywords (*external ideas*) to trigger creative reasoning, rather than relying on internal randomness.

🧠 **Waypoint reasoning** — generates executable solutions through structured checkpoints instead of free-form chain-of-thought.

## 🚀 Coming Soon

🔓 **Code release**

🧪 **Plug-and-play APIs**

🌐 **Interactive demo**

## 📖 How to Cite

If you use MetaMuse in your research, please cite:

```bibtex
@article{ma2025algorithm,
  title={Algorithm Generation via Creative Ideation},
  author={Ma, Ruiying and Liang, Chieh-Jan Mike and Gao, Yanjie and Yan, Francis Y.},
  journal={arXiv preprint arXiv:2510.03851},
  year={2025}
}
```
