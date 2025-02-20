import os
import argparse
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def _parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument("--train_test_split_ratio", type=float, default=0.2)
    parser.add_argument("--local_path", type=str, default="/opt/ml/processing")

    return parser.parse_known_args()


if __name__ == "__main__":

    ### Command line parser
    args, _ = _parse_args()

    DATA_DIR = os.path.join(args.local_path, "input")
    print(f"Data directory is {DATA_DIR}")
        
    # Get TCGA BRCA Gene Expression Data
    os.system(f"wget https://tcga.xenahubs.net/download/TCGA.BRCA.sampleMap/HiSeqV2_PANCAN.gz -nc -nv -P {DATA_DIR}/")
    os.system(f"gzip -df {DATA_DIR}/HiSeqV2_PANCAN.gz")

    # Get TCGA BRCA Phenotype Data
    os.system(f"wget https://tcga.xenahubs.net/download/TCGA.BRCA.sampleMap/BRCA_clinicalMatrix -nc -nv -P {DATA_DIR}/")

    ### Load Gene Expression RNA-seq
    print(os.listdir(DATA_DIR))
    print(os.path.join(DATA_DIR, "HiSeqV2_PANCAN"))
    genom = pd.read_csv(os.path.join(DATA_DIR, "HiSeqV2_PANCAN"), sep="\t")
    genom_identifiers = genom["sample"].values.tolist()

    ### Load Phenotypes
    phenotypes = pd.read_csv(os.path.join(DATA_DIR, "BRCA_clinicalMatrix"), sep="\t")

    #### Keep `HER2_Final_Status_nature2012` target variables
    phenotypes_subset = phenotypes[
        ["sampleID", "HER2_Final_Status_nature2012"]
    ].reset_index(drop=True)
    phenotypes_subset.fillna("Negative", inplace=True)

    ### Transpose Methylation and Gene Expression datasets in order to join with Phenotypes on sampleID
    genom_transpose = (
        genom.set_index("sample")
        .transpose()
        .reset_index()
        .rename(columns={"index": "sampleID"})
    )

    ### Merge datasets
    df = pd.merge(phenotypes_subset, genom_transpose, on="sampleID", how="left")

    ### Encode target
    df["target"] = [
        0 if t == "Negative" else 1 for t in df["HER2_Final_Status_nature2012"]
    ]
    df = df.drop(["HER2_Final_Status_nature2012", "sampleID"], axis=1)
    ## Move target to first column
    df.insert(loc=0, column="target", value=df.pop("target"))
    ## Drop rows with NaN values
    df = df.dropna()

    ### Train-Valid-Test split
    # Hold out 20% of the data for validation
    train_df, val_df = train_test_split(df, test_size=args.train_test_split_ratio)

    print(
        f"The training data has {train_df.shape[0]} records and {train_df.shape[1]} columns."
    )
    print(
        f"The validation data has {val_df.shape[0]} records and {val_df.shape[1]} columns."
    )

    # Save data
    os.makedirs(os.path.join(args.local_path, "output/train"), exist_ok=True)
    training_output_path = os.path.join(args.local_path, "output/train/train.csv")
    train_df.to_csv(training_output_path, header=False, index=False)
    print(f"Training data saved to {training_output_path}")

    os.makedirs(os.path.join(args.local_path, "output/val"), exist_ok=True)
    val_output_path = os.path.join(args.local_path, "output/val/val.csv")
    val_df.to_csv(val_output_path, header=False, index=False)
    print(f"Validation data saved to {val_output_path}")
