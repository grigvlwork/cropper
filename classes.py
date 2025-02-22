from math import ceil

import cv2
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QBrush, QImage, QPen
import pickle
import os
import shutil
from PIL import Image
from typing import Callable, NamedTuple, Union
from functions import *

STEPS = ["vertical_cut", "horizontal_cut", "orientation", "rotation",
         "word_select", "letter_select", "output"]
TEXT_STEPS = ["вертикальный разрез", "горизонтальный разрез",
              "ориентация бланка", "вращение", "выбор слов",
              "выбор букв", "вывод результата"]
GRID_WIDTH = 3240
GRID_HEIGHT = 2000
ANGLE_SCALE = 1
DELTA_ANGLE = 0.1


class Action(NamedTuple):
    type: str  # "cut", "crop", "rotate"
    value: Union[int, float, tuple]  # Число или кортеж
    final: bool


class Mylabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class Project:
    def __init__(self, directory_name=None, file_project_name=None):
        self.work_dir = directory_name
        self.file_project_name = file_project_name
        self.current_step = 0
        self.files = None
        self.check_list = None
        self.steps = STEPS
        self.text_steps = TEXT_STEPS
        self.actions = None  # действия на текущем этапе
        self.history = None  # словарь {этап: actions}
        if directory_name is not None:
            self.load_project()
        else:
            self.actions = dict()  # {индекс_изображения: действие}

    def add_action_to_image(self, image_index, action: Action):
        self.actions[image_index] = action

    def remove_action_from_image(self, image_index):
        if image_index in self.actions:
            self.actions.pop(image_index)

    def create_viewer(self, path, image_index, container_size):
        if image_index in self.actions.keys():
            return ImageViewer(path, image_index, self.add_action_to_image, self.remove_action_from_image,
                               self.current_step, current_action=self.actions[image_index],
                               container_size=container_size)
        return ImageViewer(path, image_index, self.add_action_to_image, self.remove_action_from_image,
                           self.current_step, container_size=container_size)

    def __getstate__(self) -> dict:
        state = dict()
        state["work_dir"] = self.work_dir
        state["file_project_name"] = self.file_project_name
        state["current_step"] = self.current_step
        state["files"] = self.files
        state["check_list"] = self.check_list
        state["history"] = self.history
        return state

    def get_current_files(self):
        # files, _, __ = zip(*self.action_steps[self.current_step])
        return self.files

    def get_current_action(self):
        return self.actions

    def get_current_text_step(self):
        return self.text_steps[self.current_step]

    def set_check_list(self, check_list):
        self.check_list = check_list

    def get_current_check_list(self):
        return self.check_list

    def get_current_step_dir(self):
        return self.work_dir + '/processing/' + self.steps[self.current_step]

    def __setstate__(self, state: dict):
        self.work_dir = state["work_dir"]
        self.file_project_name = state["file_project_name"]
        self.current_step = state["current_step"]
        # self.actions = state["actions"]
        self.files = state["files"]
        self.check_list = state["check_list"]
        self.history = state["history"]
        self.actions = self.history[self.current_step]

    def load_project(self):
        file_name = self.get_possible_project_name()
        try:
            with open(file_name, "rb") as fp:
                temp = pickle.load(fp)
                self.work_dir = temp.work_dir
                self.file_project_name = temp.file_project_name
                self.current_step = temp.current_step
                self.files = temp.files
                self.check_list = temp.check_list
                self.history = temp.history
                self.actions = self.history[self.current_step]
                return True
        except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            return False

    def save_project(self):
        try:
            if self.history is None:
                self.history = dict()
            self.history[self.current_step] = self.actions
            with open(self.file_project_name, "wb") as fp:
                pickle.dump(self, fp)
                return True
        except OSError as e:
            print("OS error({0}): {1}".format(e.errno, e.strerror))
            return False

    def get_possible_project_name(self):
        return self.work_dir + '/processing/' + os.path.basename(self.work_dir) + ".blr"

    def new_project(self, window):
        self.work_dir = ""
        self.work_dir = QFileDialog.getExistingDirectory(window, 'Select Folder')
        # Проверить что в папке нет уже существующего проекта, если есть,
        # то либо загружаем старый, либо создаем новый
        if self.work_dir == "":
            return False
        possible_project_name = self.get_possible_project_name()
        if os.path.isfile(possible_project_name):
            reply = QMessageBox.question(None, 'Проект существует',
                                         'В папке имеется проект, загрузить его?',
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.load_project()
                return True
        else:
            if self.make_structure():
                self.file_project_name = possible_project_name
                self.current_step = 0
                self.load_current_files()
                self.save_project()
                return True
        return False

    def make_structure(self):
        try:
            if not os.path.isdir(self.work_dir + '/processing'):
                os.mkdir(self.work_dir + '/processing')
            for step in self.steps:
                if not os.path.isdir(self.work_dir + '/processing/' + step):
                    os.mkdir(self.work_dir + '/processing/' + step)
            files = os.listdir(self.work_dir)
            for fname in files:
                if os.path.isfile(os.path.join(self.work_dir, fname)):
                    shutil.copy2(os.path.join(self.work_dir, fname), self.work_dir + '/processing/vertical_cut')
            return True
        except OSError:
            return False

    def crop_image(self, file, crop_params):
        """
        Обрезает изображение с учетом отрицательной координаты x.

        :param file: Имя входного файла изображения
        :param crop_params: Кортеж (x, y)
        """
        image_parts = [(0, 0, 1675, 152), (1795, 0, 2155, 152),
                       (2395, 0, 2875, 152), (2995, 0, 3235, 152),
                       (120, 185, 1560, 337), (1795, 185, 3235, 337)]
        for i in range(2, 11):
            y0 = i * 185
            image_parts.append((120, y0, 1560, y0 + 152))
            image_parts.append((1795, y0, 3235, y0 + 152))
        # Открываем изображение
        image = Image.open(file)
        width, height = image.size
        x, y = crop_params
        if x < 0:
            # Создаем новое изображение с увеличенной шириной
            new_width = width + ceil(abs(x))
            new_image = Image.new("RGB", (new_width, height), (255, 255, 255))  # Белый фон
            new_image.paste(image, (ceil(abs(x)), 0))  # Вставляем исходное изображение справа
            image = new_image
            x = 0  # Теперь x начинается с 0
        for i in range(len(image_parts)):
            p = image_parts[i]
            output_file = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                          '/' + os.path.splitext(os.path.basename(file))[0] + 'w' + str(i).zfill(2) + \
                          os.path.splitext(os.path.basename(file))[1]
            cropped_image = image.crop((x + p[0], y + p[1], x + p[2], y + p[3]))
            cropped_image.save(output_file)

    def apply_action(self, file, action):
        if action.type == 'vertical_cut':
            left_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                        '/' + os.path.splitext(os.path.basename(file))[0] + 'v0' + \
                        os.path.splitext(os.path.basename(file))[1]
            right_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                         '/' + os.path.splitext(os.path.basename(file))[0] + 'v1' + \
                         os.path.splitext(os.path.basename(file))[1]
            # Открываем исходное изображение
            image = Image.open(file)
            width, height = image.size
            # Координата X для вертикального разреза
            cut_position = action.value  # Например, разрез посередине
            # Создаем две новые области для кропа
            left_half = image.crop((0, 0, cut_position, height))
            right_half = image.crop((cut_position, 0, width, height))
            # Сохраняем левую половину
            left_half.save(left_name)
            # Сохраняем правую половину
            right_half.save(right_name)
        elif action.type == 'horizontal_cut':
            top_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                       '/' + os.path.splitext(os.path.basename(file))[0] + 'h0' + \
                       os.path.splitext(os.path.basename(file))[1]
            bottom_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                          '/' + os.path.splitext(os.path.basename(file))[0] + 'h1' + \
                          os.path.splitext(os.path.basename(file))[1]
            # Открываем исходное изображение
            image = Image.open(file)
            width, height = image.size
            # Координата Y для горизонтального разреза
            cut_position = action.value  # Например, разрез посередине
            # Создаем две новые области для кропа
            top_half = image.crop((0, 0, width, cut_position))
            bottom_half = image.crop((0, cut_position, width, height))
            # Сохраняем верхнюю половину
            top_half.save(top_name)
            # Сохраняем нижнюю половину
            bottom_half.save(bottom_name)
        elif action.type == 'orientation':
            new_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                       '/' + os.path.basename(file)
            image = Image.open(file).rotate(180)
            image.save(file)
            self.angle_adjust(file, new_name)
        elif action.type == 'rotation':
            new_name = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                       '/' + os.path.basename(file)
            image = Image.open(file).rotate(-action.value)
            image.save(new_name)
        elif action.type == 'word_select':
            self.crop_image(file, action.value)

    def angle_adjust(self, file, new_file):
        img = cv2.imread(file)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_area = 0
        best_rect = None
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max_area:
                max_area = area
                best_rect = cv2.minAreaRect(cnt)
        if best_rect is not None:
            angle = best_rect[-1]
            if -10 < angle < 10:
                image = Image.open(file)
                rotated_image = image.rotate(angle, expand=True)
                rotated_image.save(new_file)
            else:
                image = Image.open(file)
                # rotated_image = image.rotate(angle, expand=True)
                image.save(new_file)

    def next_step(self):
        try:
            for filename in os.listdir(self.work_dir + '/processing/' + STEPS[self.current_step + 1]):
                file_path = os.path.join(self.work_dir + '/processing/' + STEPS[self.current_step + 1], filename)
                os.remove(file_path)
            if os.path.isdir(self.work_dir + '/processing/' + STEPS[self.current_step + 1] + '/thumbnails'):
                shutil.rmtree(self.work_dir + '/processing/' + STEPS[self.current_step + 1] + '/thumbnails')
            if not os.path.isdir(self.work_dir + '/processing/' + STEPS[self.current_step + 1] + '/thumbnails'):
                os.mkdir(self.work_dir + '/processing/' + STEPS[self.current_step + 1] + '/thumbnails')
        except OSError:
            return False
        if self.current_step in (0, 1, 2, 3, 4):
            check_list = self.get_current_check_list()
            files = self.get_current_files()
            actions = self.get_current_action()
            for i in range(len(files)):
                if check_list[i]:
                    if i in self.actions:
                        self.apply_action(files[i], actions[i])
                    else:
                        file = self.files[i]
                        new_file = self.work_dir + '/processing/' + self.steps[self.current_step + 1] + \
                                   '/' + os.path.basename(file)
                        if self.current_step in (0, 1):
                            try:
                                shutil.copy2(file, new_file)
                            except OSError:
                                return False
                        elif self.current_step == 2:
                            self.angle_adjust(file, new_file)

        self.actions = dict()
        self.check_list = None
        self.current_step += 1
        self.load_current_files()
        self.generate_thumbnails()
        self.save_project()
        return self.current_step

    def load_current_files(self):
        if self.work_dir is None:
            return ''
        else:
            current_step_dir = self.work_dir + '/processing/' + self.steps[self.current_step]
            files = [os.path.join(current_step_dir, f) for f in os.listdir(current_step_dir) if
                     os.path.isfile(os.path.join(current_step_dir, f))]
            self.files = files
            return files

    def generate_thumbnails(self):
        thumbnails = []
        for file in self.load_current_files():
            image = Image.open(file)
            image.thumbnail((400, 400))
            new_name = self.work_dir + '/processing/' + self.steps[self.current_step] + \
                       '/thumbnails/' + os.path.splitext(os.path.basename(file))[0] + '.jpg'
            image = image.convert('RGB')
            image.save(new_name, format='JPEG')
            thumbnails.append(new_name)
        return thumbnails

    def get_current_thumbnails(self):
        if os.path.isdir(self.work_dir + '/processing/' + self.steps[self.current_step] + '/thumbnails'):
            td = self.work_dir + '/processing/' + self.steps[self.current_step] + '/thumbnails'
            thumbnails = [os.path.join(td, f) for f in os.listdir(td) if
                          os.path.isfile(os.path.join(td, f))]
            return thumbnails
        else:
            os.mkdir(self.work_dir + '/processing/' + self.steps[self.current_step] + '/thumbnails')
            return self.generate_thumbnails()


class ImageViewer(QGraphicsView):
    def __init__(self, image_path, image_index,
                 on_action_added: Callable[[int, str], None],
                 on_action_removed: Callable[[int], None],
                 current_step,
                 current_action=None,
                 container_size=(2000, 1000)):
        super().__init__()
        self.setMouseTracking(True)
        self.borders = None
        self.angle = None
        self.rotation_line = None
        self.rotation_handle = None
        self.current_step = current_step
        self.image_index = image_index
        self.on_action_added = on_action_added
        self.on_action_removed = on_action_removed
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.image_path = image_path
        self.pixmap = QPixmap(image_path)
        self.pos_in_original_image = None
        self.right_btn = False
        original_width = self.pixmap.width()
        original_height = self.pixmap.height()
        # Масштабирование изображения
        self.container_width, self.container_height = container_size
        scaled_pixmap = self.pixmap.scaled(self.container_width, self.container_height,
                                           transformMode=Qt.TransformationMode.SmoothTransformation,
                                           aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        self.pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scale_x = original_width / scaled_pixmap.width()
        self.scale_y = original_height / scaled_pixmap.height()
        self.mouse_press_pos = None
        self.line = None
        self.grid = None
        self.current_action = current_action
        if current_action is not None:
            self.apply_action()
        else:
            self.current_line = None

    def apply_action(self):
        if self.current_action.final:
            color = Qt.GlobalColor.green
        else:
            color = Qt.GlobalColor.red
        if self.current_action.type == 'vertical_cut':
            x = self.current_action.value / self.scale_x
            self.line = QGraphicsLineItem(x, 0, x, self.pixmap_item.pixmap().height())
            self.line.setPen(color)
            self.scene.addItem(self.line)
        elif self.current_action.type == 'horizontal_cut':
            y = self.current_action.value / self.scale_y
            self.line = QGraphicsLineItem(0, y, self.pixmap_item.pixmap().width(), y)
            self.line.setPen(color)
            self.scene.addItem(self.line)
        elif self.current_action.type == 'orientation':
            image = Image.open(self.image_path)
            # Поворачиваем изображение на 180 градусов
            rotated_image = image.rotate(180, expand=True)
            self.scene.removeItem(self.pixmap_item)
            self.pixmap = pil2pixmap(rotated_image)
            scaled_pixmap = self.pixmap.scaled(self.container_width, self.container_height,
                                               transformMode=Qt.TransformationMode.SmoothTransformation,
                                               aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
            self.scene.addItem(self.pixmap_item)
        elif self.current_action.type == 'rotation':
            image = Image.open(self.image_path)
            rotated_image = image.rotate(-self.current_action.value, expand=True)
            self.scene.removeItem(self.pixmap_item)
            self.pixmap = pil2pixmap(rotated_image)
            scaled_pixmap = self.pixmap.scaled(self.container_width, self.container_height,
                                               transformMode=Qt.TransformationMode.SmoothTransformation,
                                               aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
            self.scene.addItem(self.pixmap_item)
        elif self.current_action.type == 'word_select':
            x = self.current_action.value[0] / self.scale_x
            y = self.current_action.value[1] / self.scale_y
            w = GRID_WIDTH / self.scale_x
            h = GRID_HEIGHT / self.scale_y
            self.grid = QGraphicsRectItem()
            self.grid.setRect(QRectF(x, y, w, h))
            self.grid.setPen(Qt.GlobalColor.red)
            self.scene.addItem(self.grid)
        elif self.current_action.type == 'letter_select':
            rectangles = self.current_action.value
            self.borders = []
            for rectangle in rectangles:
                x = rectangle[0] / self.scale_x
                y = rectangle[1] / self.scale_y
                w = rectangle[2] / self.scale_x
                h = rectangle[3] / self.scale_y
                rect = QGraphicsRectItem()
                rect.setRect(QRectF(x, y, w, h))
                rect.setPen(color)
                self.borders.append(rect)
                self.scene.addItem(rect)

    def contour(self):
        rectangles = self.contouring(self.image_path)
        self.current_action = Action(type='letter_select', value=rectangles, final=False)
        self.apply_action()
        self.add_action()

    def contouring(self, file):
        img = cv2.imread(file)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_width, max_width = 50, 100  # Ширина в пределах 110–130 пикселей
        min_height, max_height = 60, 170  # Высота в пределах 170–200 пикселей
        rectangles = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if (min_width <= w <= max_width and
                    min_height <= h <= max_height):
                rectangles.append((x, y, w, h))  # Добавляем координаты прямоугольника в список
        return tuple(rectangles)

    def add_action(self):
        if self.on_action_added:
            self.on_action_added(self.image_index, self.current_action)  # Сообщаем Project

    def remove_action(self):
        if self.on_action_removed:
            self.on_action_removed(self.image_index)  # Сообщаем Project

    def remove_line(self):
        if self.line is not None:
            self.scene.removeItem(self.line)
            self.line = None
            self.remove_action()
            self.current_action = None

    def flip(self):
        if self.current_step == 2:  # Переворот
            # Открываем изображение
            image = Image.open(self.image_path)
            # Поворачиваем изображение на 180 градусов
            rotated_image = image.rotate(180, expand=True)
            self.scene.removeItem(self.pixmap_item)
            self.pixmap = pil2pixmap(rotated_image)
            scaled_pixmap = self.pixmap.scaled(self.container_width, self.container_height,
                                               transformMode=Qt.TransformationMode.SmoothTransformation,
                                               aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
            self.scene.addItem(self.pixmap_item)
            self.current_action = Action(type='orientation', value=180, final=True)
            self.add_action()

    def add_line(self):
        if self.line is not None:
            return
        if self.current_step == 0:  # Вертикальный разрез
            self.line = QGraphicsLineItem(self.pixmap_item.pixmap().width() // 2, 0,
                                          self.pixmap_item.pixmap().width() // 2, self.pixmap_item.pixmap().height())
            self.line.setPen(Qt.GlobalColor.red)
            self.scene.addItem(self.line)
            pos_in_original_image = QPointF(
                self.pixmap_item.pixmap().width() // 2 * self.scale_x,
                0
            )
            self.current_action = Action(type='vertical_cut', value=int(pos_in_original_image.x()), final=False)
            self.add_action()
        elif self.current_step == 1:  # Горизонтальный разрез
            self.line = QGraphicsLineItem(0, self.pixmap_item.pixmap().height() // 2,
                                          self.pixmap_item.pixmap().width(), self.pixmap_item.pixmap().height() // 2)
            self.line.setPen(Qt.GlobalColor.red)
            self.scene.addItem(self.line)
            pos_in_original_image = QPointF(
                0, self.pixmap_item.pixmap().height() // 2 * self.scale_y
            )
            self.current_action = Action(type='horizontal_cut', value=int(pos_in_original_image.y()), final=False)
            self.add_action()

    def rotate(self):
        if self.rotation_line is not None:
            return
        self.angle = 0
        self.rotation_line = QGraphicsLineItem(0, self.pixmap_item.pixmap().height() // 2,
                                               self.pixmap_item.pixmap().width(),
                                               self.pixmap_item.pixmap().height() // 2)
        self.rotation_line.setPen(Qt.GlobalColor.red)
        self.scene.addItem(self.rotation_line)
        self.current_action = Action(type='rotate', value=0, final=False)
        self.add_action()

    def add_grid(self):
        if self.grid is not None:
            return
        x = 0
        y = 0
        w = GRID_WIDTH / self.scale_x
        h = GRID_HEIGHT / self.scale_y
        self.grid = QGraphicsRectItem()
        self.grid.setRect(QRectF(x, y, w, h))
        self.grid.setPen(Qt.GlobalColor.red)
        self.scene.addItem(self.grid)
        self.current_action = Action(type='word_select',
                                     value=(x * self.scale_x, y * self.scale_y),
                                     final=False)
        self.add_action()

    def add_final_line(self):
        if self.line is not None:
            self.scene.removeItem(self.line)
            if self.current_action.type == 'vertical_cut':
                x = self.current_action.value / self.scale_x
                self.line = QGraphicsLineItem(x, 0, x, self.pixmap_item.pixmap().height())
                self.line.setPen(Qt.GlobalColor.green)
                self.scene.addItem(self.line)
                self.current_action = Action(type=self.current_action.type,
                                             value=self.current_action.value,
                                             final=True)
            elif self.current_action.type == 'horizontal_cut':
                y = self.current_action.value / self.scale_y
                self.line = QGraphicsLineItem(0, y, self.pixmap_item.pixmap().width(), y)
                self.line.setPen(Qt.GlobalColor.green)
                self.scene.addItem(self.line)
                self.current_action = Action(type=self.current_action.type,
                                             value=self.current_action.value,
                                             final=True)

    def fix_rotation(self):
        self.current_action = Action(type=self.current_action.type,
                                     value=self.current_action.value,
                                     final=True)

    def get_index(self):
        return self.image_index

    def mousePressEvent(self, event):
        if self.current_action is None:
            return
        if self.current_action.final:
            self.mouse_press_pos = None
            return
        if event.button() == Qt.MouseButton.LeftButton and (self.current_step in (0, 1, 3, 4)):
            self.mouse_press_pos = QPointF(event.pos())
            self.right_btn = False
        if event.button() == Qt.MouseButton.RightButton and self.current_step == 3:
            self.mouse_press_pos = QPointF(event.pos())
            self.right_btn = True

    def mouseMoveEvent(self, event):
        self.pos = QPointF(event.scenePosition())
        if self.current_action is None:
            return
        if self.current_action.final:
            self.mouse_press_pos = None
            return
        if self.mouse_press_pos is not None and (self.current_step in (0, 1)):
            new_pos = QPointF(self.line.pos())
            if self.current_step == 0:  # Вертикальный разрез
                delta = QPointF(event.pos()) - self.mouse_press_pos
                delta.setY(0)
                new_pos += delta
            elif self.current_step == 1:  # Горизонтальный разрез, настройка угла
                delta = QPointF(event.pos()) - self.mouse_press_pos
                delta.setX(0)
                new_pos += delta
            self.line.setPos(new_pos)
            self.mouse_press_pos = QPointF(event.pos())
        elif self.mouse_press_pos is not None and self.current_step == 4:
            new_pos = QPointF(self.grid.pos())
            delta = event.pos() - self.mouse_press_pos
            new_pos += delta
            self.grid.setPos(new_pos)
            self.mouse_press_pos = QPointF(event.pos())
        elif self.mouse_press_pos is not None and self.current_step == 3:
            delta = QPointF(event.pos()) - self.mouse_press_pos
            if not self.right_btn:
                self.angle += delta.x() * DELTA_ANGLE
                self.pixmap_item.setRotation(self.angle)
            else:
                new_pos = self.rotation_line.pos()
                delta.setX(0)
                new_pos += delta
                self.rotation_line.setPos(new_pos)
            self.mouse_press_pos = QPointF(event.pos())
        elif self.current_step == 5:
            pos = QPointF(event.scenePosition())
            for i, rect in enumerate(self.borders):
                if rect.contains(pos):
                    rect.setPen(QPen(Qt.GlobalColor.yellow, 3))
                    for j, other_rect in enumerate(self.borders):
                        if j != i:
                            other_rect.setPen(QPen(Qt.GlobalColor.red, 1))

    def mouseReleaseEvent(self, event):
        if self.current_action is None:
            return
        if self.current_action.final:
            self.mouse_press_pos = None
            return
        if event.button() == Qt.MouseButton.LeftButton and (self.current_step in (0, 1, 3, 4)):
            scene_pos = self.mapToScene(event.pos()).toPoint()
            item_pos = self.itemAt(scene_pos)
            self.current_action = None
            if self.current_step == 0:  # Вертикальный разрез
                if isinstance(item_pos, QGraphicsPixmapItem):
                    pixmap_pos = item_pos.mapFromScene(QPointF(scene_pos))
                    pos_in_original_image = QPointF(pixmap_pos.x() * self.scale_x,
                                                    pixmap_pos.y() * self.scale_y)
                    self.current_action = Action(type='vertical_cut',
                                                 value=int(pos_in_original_image.x()),
                                                 final=False)
            elif self.current_step == 1:  # Горизонтальный разрез
                pixmap_pos = item_pos.mapFromScene(QPointF(scene_pos))
                pos_in_original_image = QPointF(pixmap_pos.x() * self.scale_x,
                                                pixmap_pos.y() * self.scale_y)
                self.current_action = Action(type='horizontal_cut',
                                             value=int(pos_in_original_image.y()),
                                             final=False)
            elif self.current_step == 3:
                if not self.right_btn:
                    delta = QPointF(event.pos()) - self.mouse_press_pos
                    self.angle += delta.x() * DELTA_ANGLE
                    self.current_action = Action(type='rotation',
                                                 value=self.angle,
                                                 final=False)

            elif self.current_step == 4:
                pos_in_original_image = QPointF(0 + self.grid.pos().x() * self.scale_x,
                                                0 + self.grid.pos().y() * self.scale_y)
                self.current_action = Action(type='word_select',
                                             value=(pos_in_original_image.x(), pos_in_original_image.y()),
                                             final=False)
            self.add_action()
        self.mouse_press_pos = None
