from paddleocr import PaddleOCR, draw_ocr
import cv2 as cv
import torch
import math
from functions import get_center_point, get_distance, xy_in_xywh, get_xyxy_from_box, get_bound_xyxy


class TextEncoder:
    """get the text encoding of the raw image"""
    def __init__(self) -> None:
        pass
    
    def _get_text_size(self, box, text_len):
        print(box)
        '''in the box, the height dim is index 1, width dim is index 0'''
        height = (abs(box[0][1]-box[3][1]) + abs(box[1][1]-box[2][1]))/2
        width = (abs(box[1][0]-box[0][0]) + abs(box[2][0]-box[3][0]))/(2*text_len)
        return width, height
    
    def _get_box_area(self, box):
        height = (abs(box[0][1]-box[3][1]) + abs(box[1][1]-box[2][1]))/2
        width = (abs(box[1][0]-box[0][0]) + abs(box[2][0]-box[3][0]))/2
        return width*height

    def get_nearest_text(self, img, show=False):
        '''get the nearest text w.r.t the center of the image'''
        ocr = PaddleOCR(lang='en')
        result = ocr.ocr(img)
        for res in result: print(res)
        if result == []: return None, None, None
        img_center = [img.shape[0]/2, img.shape[1]/2]
        boxes = [line[0] for line in result]
        texts = [line[1][0] for line in result]
        box_centers = [get_center_point(box) for box in boxes]
        distances = [get_distance(box_center, img_center) for box_center in box_centers]
        areas = [self._get_box_area(box) for box in boxes]
        nearest_index = max(range(len(distances)), key=areas.__getitem__)
        nearest_text = texts[nearest_index]
        nearest_box = boxes[nearest_index]
        text_shape = self._get_text_size(nearest_box, len(nearest_text))
        print("nearest box center:", box_centers[nearest_index])
        text_box = boxes[nearest_index]
        if show:
            from PIL import Image
            im_show = draw_ocr(img, boxes)
            im_show = Image.fromarray(im_show)
            im_show.save('images/ocr_result.jpg')
        return nearest_text, text_shape, text_box


class ShapeEncoder:
    def __init__(self, weight_path='yolov5/weights/best.pt') -> None:
        self.model = torch.hub.load('yolov5', 'custom', path=weight_path, source='local')
        pass

    def get_relevant_shape(self, img, text_center=[359.75, 215.0]):
        result = self.model(img)
        result.save()
        if [*result.xywh[0].shape][0] == 0: return []
        logo_box_centers = [res[:2] for res in result.xywh[0]] # center of each box
        distances = [get_distance(text_center, logo_center) for logo_center in logo_box_centers] # dis(shape center, text center)
        sizes = [res[2]+res[3] for res in result.xywh[0]] # size of each box
        confs = [res[5] for res in result.xywh[0]] # confidence of each box
        # nearest_index = min(range(len(distances)), key=distances.__getitem__)
        scores = []
        for i in range(len(distances)):
            score = sizes[i]*confs[i]/distances[i]
            scores.append(score)
        nearest_index = max(range(len(scores)), key=scores.__getitem__)
        nearest_logo_box = result.xywh[0][nearest_index][:4]
        '''get relevant logo indexs'''
        relevant_logo_ids = []
        for id in range(len(logo_box_centers)):
            if xy_in_xywh(logo_box_centers[id], nearest_logo_box):
                relevant_logo_ids.append(id)
        '''get relevant logo infos via ids'''
        relevant_logos = []
        for logo_id in relevant_logo_ids:
            logo_name_id = int(result.pred[0][logo_id][5])
            logo = {'xyxy': result.xyxy[0][logo_id][:4], 'name': result.names[logo_name_id]}
            relevant_logos.append(logo)
        # print(relevant_logos)
        return relevant_logos


class LogoEncoder:
    def __init__(self) -> None:
        self.text_encoder = TextEncoder()
        self.shape_encoder = ShapeEncoder()
    
    def draw_plus(self, ascii_mat, Sx, Sy, W, H):
        size = (W+H)//2
        if size <= 2:
            ascii_mat[Sy][Sx] = '+'
        elif size <= 4:
            ascii_mat[Sy][Sx+2] = "|"
            ascii_mat[Sy+1][Sx:Sx+5] = ["-", "-", "+", "-", "-"]
            ascii_mat[Sy+2][Sx+2] = "|"
            pass
        else: pass
        pass

    def draw_square(self, ascii_mat, Sx, Sy, W, H):
        size = (W+H)//2
        if size <= 2:
            ascii_mat[Sy][Sx:Sx+3] = ['[', '_', ']']
        else:
            for i in range(W):
                ascii_mat[Sy][i+Sx] = "-"
                ascii_mat[Sy+H][i+Sx] = "-"
            for j in range(H):
                ascii_mat[Sy+j][Sx] = "|"
                ascii_mat[Sy+j][Sx+W] = "|"
        pass

    def draw_triangle(self, ascii_mat, Sx, Sy, W, H):
        size = (W+H)//2
        if size <= 1:
            ascii_mat[Sy][Sx] = "^"
        elif size <=4:
            for i in range(3):
                ascii_mat[Sy+i][Sx+2-i] = "/"
            for i in range(3):
                ascii_mat[Sy+i][Sx+3+i] = "\\"
            ascii_mat[Sy+2][Sx+1] = ascii_mat[Sy+2][Sx+4] = "_"
        else:
            pass
        pass

    def draw_circle(self, ascii_mat, Sx, Sy, W, H):
        size = (W+H)//2
        if size <= 2:
            ascii_mat[Sy][Sx] = "O"
        elif size <= 4:
            ascii_mat[Sy][Sx+1] = ascii_mat[Sy][Sx+3] = 'o'
            ascii_mat[Sy+1][Sx] = ascii_mat[Sy+1][Sx+4] = 'o'
            ascii_mat[Sy+2][Sx+1] = ascii_mat[Sy+2][Sx+3] = 'o'
        else:
            center = [Sx+round(W/2), Sy+round(H/2)]
            Sx = center[0]-5
            Sy = center[1]-3
            ascii_mat[Sy][Sx+4] = ascii_mat[Sy][Sx+7] = "="
            ascii_mat[Sy+1][Sx+1] = ascii_mat[Sy+1][Sx+10] = "="
            ascii_mat[Sy+2][Sx] = ascii_mat[Sy+2][Sx+11] = "="
            ascii_mat[Sy+3][Sx] = ascii_mat[Sy+3][Sx+11] = "="
            ascii_mat[Sy+4][Sx+1] = ascii_mat[Sy+4][Sx+10] = "="
            ascii_mat[Sy+5][Sx+4] = ascii_mat[Sy+5][Sx+7] = "="
        pass
    
    def draw_ellipse(self, ascii_mat, Sx, Sy, W, H):
        pass

    def draw_cross(self, ascii_mat, Sx, Sy, W, H):
        size = (W+H)//2
        if size <= 2:
            ascii_mat[Sy][Sx] = "X"
        elif size <= 4:
            ascii_mat[Sy][Sx] = ascii_mat[Sy+1][Sx+1] = "\\"
            ascii_mat[Sy][Sx+1] = ascii_mat[Sy+1][Sx] = "/"
        else:
            ascii_mat[Sy][Sx] = ascii_mat[Sy+2][Sx+2] = "\\"
            ascii_mat[Sy][Sx+2] = ascii_mat[Sy+2][Sx] = "/"
            ascii_mat[Sy+1][Sx+1] = "X"
        pass

    def draw_hexagon(self, ascii_mat, Sx, Sy, W, H):
        pass

    def draw_rhombus(self, ascii_mat, Sx, Sy, W, H):
        pass

    def draw_inv_triangle(self, ascii_mat, Sx, Sy, W, H):
        pass

    def draw_unk(self, ascii_mat, Sx, Sy, W, H):
        pass

    def encode_text(self, img, save_path='results/text.txt'):
        text, _, __ = self.text_encoder.get_nearest_text(img)
        if text == None: text = ""
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'The encoding file saved sucessfully at {save_path} !')
        return text

    def encode_logo(self, img, save_path='results/logo.txt'):
        '''get text info'''
        text, text_shape, text_box = self.text_encoder.get_nearest_text(img, show=True)
        # bad case where no text is detected in the image
        if text == None: return ""
        # if text exist in the image, do the subsequent stuff
        '''get shape info'''
        relevant_shapes = self.shape_encoder.get_relevant_shape(img, text_center=get_center_point(text_box))
        w, h = text_shape
        '''get bounding box of all boxes'''
        x_min_t, y_min_t, x_max_t, y_max_t = get_xyxy_from_box([text_box])
        x_min_s, y_min_s, x_max_s, y_max_s = get_bound_xyxy([shape['xyxy'] for shape in relevant_shapes])
        x_min = min(x_min_t, x_min_s)-2*w
        y_min = min(y_min_t, y_min_s)-2*h
        x_max = max(x_max_t, x_max_s)+2*w
        y_max = max(y_max_t, y_max_s)+2*h
        Nx = math.ceil((x_max-x_min)/w)+1
        Ny = math.ceil((y_max-y_min)/h)+1
        print(f"Nx: {Nx}, Ny:{Ny}")
        ascii_mat = [[' ' for __ in range(Nx)] for _ in range(Ny)]

        ## note: shape rander first, then text
        
        '''draw shape'''
        for shape in relevant_shapes:
            x1, y1, x2, y2 = shape['xyxy']
            name = shape['name']
            W = math.floor((x2-x1)/w)
            H = math.floor((y2-y1)/h)
            Sx = math.floor((x1-x_min)/w)
            Sy = math.floor((y1-y_min)/h)
            print(f"For shape {name}, Sx:{Sx}, Sy:{Sy}, W:{W}, H:{H}")
            if name == 'plus':
                self.draw_plus(ascii_mat, Sx, Sy, W, H)
            elif name == 'square':
                self.draw_square(ascii_mat, Sx, Sy, W, H)
            elif name == 'triangle':
                self.draw_triangle(ascii_mat, Sx, Sy, W, H)
            elif name == "circle":
                self.draw_circle(ascii_mat, Sx, Sy, W, H)
            elif name == "cross":
                self.draw_cross(ascii_mat, Sx, Sy, W, H)
            elif name == "ellipse":
                self.draw_cross(ascii_mat, Sx, Sy, W, H)
            elif name == "rhombus":
                self.draw_cross(ascii_mat, Sx, Sy, W, H)
            elif name == "inverse triangle":
                self.draw_cross(ascii_mat, Sx, Sy, W, H)
            elif name == "hexagon":
                self.draw_cross(ascii_mat, Sx, Sy, W, H)
            elif name == "unk": pass
            else: pass

        
        '''draw text in ascii_mat'''
        ## only support text in one line
        Tx = math.ceil((x_min_t-x_min)/w)
        Ty = math.ceil(((y_max_t+y_min_t)/2-y_min)/h)
        print(f"Text starting point: Tx:{Tx}, Ty:{Ty}")
        ascii_mat[Ty][Tx:(Tx+len(text))] = list(text)
        

        '''flatten two dimensional ascii array'''
        res = ""
        for line in ascii_mat:
            for c in line:
                res += c
            res += "\n"
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(res)
        print("Logo ASCII Art sucessfully saved at ", save_path)
        return res


if __name__ == "__main__":
    read_path = 'images/plus.jpg'
    save_path = 'results/test_logo.txt'
    save_text = 'results/test_text.txt'
    img = cv.imread(read_path)[:, :, ::-1]

    encoder = LogoEncoder()
    encoder.encode_text(img, save_path=save_text)
    encoder.encode_logo(img, save_path=save_path)
