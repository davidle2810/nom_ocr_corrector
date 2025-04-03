import pandas as pd
import ast
import numpy as np
from pathlib import Path


def convert_data_to_Labeltxt(df, _FolderImagesName_path, _ImageName_Column = "image_name", _PositionBBoxName_Column = "Img_Box_Coordinate" , _OCRName_Column = "SinoNom_Char"):
    df["image_name"] = df.iloc[:, 0].astype(str).apply(lambda x: "_".join(x.split("_")[:-1]) + ".png")
    grouped = df.groupby(f'{_ImageName_Column}')

    result = []
    for page_id, group in grouped:
        page_result = []
        for _, row in group.iterrows():
            points = row[f'{_PositionBBoxName_Column}']
            transcription = row[f'{_OCRName_Column}']
            
            page_result.append({"transcription": transcription, "points": points})

        result_string = "[" + ", ".join(
            [f'{{"transcription": "{item["transcription"]}", "points": {item["points"]}, "difficult": false}}' for item in page_result]
        ) + "]"

        result.append(f"{_FolderImagesName_path}/{page_id}\t{result_string}")

    output_path = f"{_FolderImagesName_path}/Label.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(result))
    list_images_name = df[f'{_ImageName_Column}'].unique().tolist()
    return list_images_name


def convert_data_to_fileStatetxt(_FolderImagesName_path, folder_list_ImageName):
    output_path = f"{_FolderImagesName_path}/fileState.txt"
    with open(f"{output_path}", "w", encoding="utf-8") as file:
        folder_name = _FolderImagesName_path
        for _imgName in folder_list_ImageName:
            file.write(f"{folder_name}/{_imgName}\t1\n")


