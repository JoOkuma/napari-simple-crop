from typing import List, Sequence, Optional

import napari
import numpy as np
from napari.layers import Layer, Labels
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSpinBox, QLabel


class SimpleZoomWidget(QWidget):
    def __init__(self, viewer: napari.Viewer):
        super().__init__()
        self.viewer = viewer
        self.prev_visibles: List[Layer] = []
        self.crop_layers: List[Layer] = []

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel('Right click a 2D slice to load crop.'))
        self.layout().addWidget(QLabel('Press Ctrl+A to toggle the visibility of the layers'))
        self.layout().addWidget(QLabel('Press Ctrl+X to close crop.'))

        self.size_spinbox = QSpinBox()
        self.size_spinbox.setValue(51)

        layout = QHBoxLayout()
        layout.addWidget(QLabel('Crop size:'))
        layout.addWidget(self.size_spinbox)

        self.layout().addLayout(layout)

        self.viewer.mouse_drag_callbacks.append(self._on_click)
        self.viewer.bind_key('Control-X', self._on_close_crop)
        self.viewer.bind_key('Control-A', self._on_toggle_visibility)

    def _get_crop(self, layer: Layer, position: Sequence[int]) -> Optional[Layer]:
        data, state, type = layer.as_layer_data_tuple()

        if type == 'image' or type == 'labels':
            state['name'] = 'Crop ' + state['name']
            half_w = self.size_spinbox.value() // 2

            slicing = []
            lower_bound = []
            for i, (c, s, d) in enumerate(zip(position, state['scale'], data.shape)):
                # hack to get 3D volume when viewing 2D
                if i in self.viewer.dims.order[-min(self.viewer.dims.ndim, 3):]:
                    l = max(0, int(c - half_w / s))
                    m = min(d, int(c + half_w / s + 1))
                else:
                    l, m = int(c), int(c + 1)
                lower_bound.append(l)
                slicing.append(slice(l, m))

            state['translate'] += np.array(lower_bound) * state['scale']
            data = data[tuple(slicing)]
            new_layer = self.viewer._add_layer_from_data(data, state, type)[0]

            if isinstance(layer, Labels):
                new_layer.color_mode = layer.color_mode

            return new_layer
        return None

    def _on_click(self, viewer: napari.Viewer, event) -> None:
        if event.button == 2:  # if right click
            layers = [l for l in viewer.layers if l not in self.crop_layers]
            for layer in layers:
                position = layer.world_to_data(viewer.cursor.position)
                new_layer = self._get_crop(layer, position)
                if new_layer is not None:
                    self.crop_layers.append(new_layer)

                if layer.visible:
                    self.prev_visibles.append(layer)
                layer.visible = False

    def _on_close_crop(self, viewer: napari.Viewer) -> None:
        for layer in self.crop_layers:
            viewer.layers.remove(layer)
        self.crop_layers.clear()

        for layer in self.prev_visibles:
            layer.visible = True
        self.prev_visibles.clear()

    def _on_toggle_visibility(self, viewer: napari.Viewer) -> None:
        for layer in self.crop_layers:
            layer.visible = not layer.visible

        for layer in self.prev_visibles:
            layer.visible = not layer.visible


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return SimpleZoomWidget
