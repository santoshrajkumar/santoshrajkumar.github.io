"""Embed every CoRL 2026 paper (title + abstract) with BAAI/bge-small-en-v1.5, as the NeurIPS/CDC explorers do.

Usage: <venv>/bin/python -I embed.py <corl2026_papers.json> <out.npy>
Rows follow the order of papers in the JSON; ids are written alongside (<out>.ids.json) so build.py can check.
"""
import json, sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

src, out = Path(sys.argv[1]), Path(sys.argv[2])
P = json.loads(src.read_text())['papers']
model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
E = model.encode([(p['title'] + '. ' + p['abstract']).strip() for p in P], batch_size=32,
                 normalize_embeddings=True, show_progress_bar=False).astype(np.float32)
np.save(out, E)
Path(str(out) + '.ids.json').write_text(json.dumps([p['id'] for p in P]))
print(E.shape)
