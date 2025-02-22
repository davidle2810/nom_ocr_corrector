# nom_ocr_corrector

nom_ocr_corrector is a multimodal sentence alignment tool for Sino-Nôm (NS) - Vietnamese (QN) parallel corpora. It uses [LASER](https://github.com/facebookresearch/LASER) embeddings and VecAlign to find sentence pairs that are similar in meaning 
and an alignment algorithm based on Levenshtein's algorithm to find the optimal alignment. 

## Building the environment

If you haven't already check out the repository:
```bash
https://github.com/davidle2810/nom_ocr_corrector.git
cd nom_ocr_corrector
```

The environment can be built using the provided environment.yml file:
```bash
conda env create -f environment.yml
conda activate ocr_corrector
python -m laserembeddings download-models
```

## Run nom_ocr_corrector
### Using provided data
```
python main_with_cmd.py --input data/truyen_cac_thanh.pdf
```

### Using your OWN data
Put the dictionaries in the `resource` folder and update their path in `sample.env` file.

You can use either a UI web interface (see [here]()) or with command line.

with command line:
```
python main_with_cmd.py --input path/to/your/data.pdf
```

