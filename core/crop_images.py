import numpy as np
import cv2
import os
import ast
import pandas as pd

from dotenv import load_dotenv
load_dotenv('.env')

def get_rotate_crop_image(img, points):
    # Use Green's theory to judge clockwise or counterclockwise
    # author: biyanhua
    d = 0.0
    for index in range(-1, 3):
        d += -0.5 * (points[index + 1][1] + points[index][1]) * (
                    points[index + 1][0] - points[index][0])
    if d < 0: # counterclockwise
        tmp = np.array(points)
        points[1], points[3] = tmp[3], tmp[1]

    try:
        img_crop_width = int(
            max(
                np.linalg.norm(points[0] - points[1]),
                np.linalg.norm(points[2] - points[3])))
        img_crop_height = int(
            max(
                np.linalg.norm(points[0] - points[3]),
                np.linalg.norm(points[1] - points[2])))
        pts_std = np.float32([[0, 0], [img_crop_width, 0],
                              [img_crop_width, img_crop_height],
                              [0, img_crop_height]])
        M = cv2.getPerspectiveTransform(points, pts_std)
        dst_img = cv2.warpPerspective(
            img,
            M, (img_crop_width, img_crop_height),
            borderMode=cv2.BORDER_REPLICATE,
            flags=cv2.INTER_CUBIC)
        dst_img_height, dst_img_width = dst_img.shape[0:2]
        if dst_img_height * 1.0 / dst_img_width >= 1.5:
            dst_img = np.rot90(dst_img)
        return dst_img
    except Exception as e:
        print(e)

def crop_image(file_name):
    crop_img_dir = os.path.join(os.environ['OUTPUT_FOLDER'],'images_label','crop_img')
    df = pd.read_excel(file_name)[['Img_Box_ID', 'Img_Box_Coordinate', 'SinoNom_Char']]
    df["image_name"] = df.iloc[:, 0].astype(str).apply(lambda x: "_".join(x.split("_")[:-1]) + ".png")
    with open(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label', 'rec_gt.txt'), 'w', encoding='utf-8') as f:
        # Iterate over each row in the DataFrame
        for _, row in df.iterrows():
            # Read the image from the file
            img = cv2.imread(os.path.join(os.environ['OUTPUT_FOLDER'],'images_label',row['image_name']))         
            # Get the rotated cropped image
            img_crop = get_rotate_crop_image(img, np.array(ast.literal_eval(row['Img_Box_Coordinate']), np.float32))
            img_name = os.path.splitext(os.path.basename(row['image_name']))[0] + '_'+row['Img_Box_ID'][-6:]
            if img_crop is None or img_crop.size == 0:
                continue
            else:
                cv2.imwrite(os.path.join(crop_img_dir,img_name), img_crop)
                f.write('crop_img/'+ img_name + '\t')
                f.write(str(row['SinoNom_Char']) + '\n')