import numpy as np

def normalize_bbox(box: list) -> list:
    """
    Converts the bounding box
    :param box: bounding box as the following format [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
    :return: converted bounding box  [top_left, top_right, bottom_right, bottom_left]
    """
    box = np.array(box)
    sorted_indices = np.lexsort((box[:, 0], box[:, 1])) 
    top_two = box[sorted_indices[:2]]
    bottom_two = box[sorted_indices[2:]] 
    top_two = top_two[np.argsort(top_two[:, 0])]
    top_left, top_right = top_two[0], top_two[1]
    bottom_two = bottom_two[np.argsort(bottom_two[:, 0])]
    bottom_left, bottom_right = bottom_two[0], bottom_two[1]
    return [top_left.tolist(), top_right.tolist(), bottom_right.tolist(), bottom_left.tolist()]

def check_overlap(cluster_range, bbox_range):
    overlap_length = min(cluster_range[1],bbox_range[1])*1.0-max(cluster_range[0],bbox_range[0])
    minimal_length = min(cluster_range[1]-cluster_range[0],bbox_range[1]-bbox_range[0])
    return overlap_length/minimal_length > 0.3

def projection_boxes(data):
    projection_result = list()
    for i, line in enumerate(data):
        bbox_range=[min(line['bbox'][0][0],line['bbox'][1][0],line['bbox'][2][0],line['bbox'][3][0]),max(line['bbox'][0][0],line['bbox'][1][0],line['bbox'][2][0],line['bbox'][3][0])]
        projection_result.append({'range':bbox_range, 'index_list':[i]})
    return projection_result

def clustering(data):
    for _ in range(3):
        clustering_result = list()
        idx = 0
        while idx < len(data):
            if (idx==0) or (check_overlap(clustering_result[-1]['range'],data[idx]['range'])==False):
                clustering_result.append({'range':data[idx]['range'], 'index_list':data[idx]['index_list']})
                idx += 1
            else:
                clustering_result[-1]['range']=[min(clustering_result[-1]['range'][0],data[idx]['range'][0]),max(clustering_result[-1]['range'][1],data[idx]['range'][1])]
                clustering_result[-1]['index_list'].extend(data[idx]['index_list'])
                data.pop(idx)
        data = clustering_result
    return clustering_result
   
def sort(data):
    for line in data:
        line['bbox']=normalize_bbox(line['bbox'])
    chunks = clustering(projection_boxes(data))
    for chunk in chunks:
        for idx in range(1, len(chunk['index_list'])):
            key = data[chunk['index_list'][idx]]
            j = idx - 1

            key_range = [min(key['bbox'][0][1],key['bbox'][1][1]),max(key['bbox'][2][1],key['bbox'][3][1])]
            while (j >= 0) and (key['bbox'][0][1] < data[chunk['index_list'][j]]['bbox'][0][1]) and (check_overlap(key_range, [min(data[chunk['index_list'][j]]['bbox'][0][1],data[chunk['index_list'][j]]['bbox'][1][1]),max(data[chunk['index_list'][j]]['bbox'][2][1],data[chunk['index_list'][j]]['bbox'][3][1])])==False):
                data[chunk['index_list'][j+1]] = data[chunk['index_list'][j]]
                j -= 1
            data[chunk['index_list'][j+1]] = key
    return data