---
pipeline_tag: image-text-to-text
license: apache-2.0
library_name: mlx
base_model: Qwen/Qwen3.5-397B-A17B
tags:
- mlx
---

# mlx-community/Qwen3.5-397B-A17B-8bit
This model was converted to MLX format from [`Qwen/Qwen3.5-397B-A17B`]() using mlx-vlm version **0.3.12**.
Refer to the [original model card](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) for more details on the model.
## Use with mlx

```bash
pip install -U mlx-vlm
```

```bash
python -m mlx_vlm.generate --model mlx-community/Qwen3.5-397B-A17B-8bit --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>
```
