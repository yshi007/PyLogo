
from math import sqrt

import numpy as np

import core.gui as gui
from core.pairs import RowCol, Pixel_xy
import core.utils as utils
# Importing this file eliminates the need for a globals declaration
# noinspection PyUnresolvedReferences
# import core.world_patch_block as wpb

from pygame.color import Color
from pygame.font import Font
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface

from typing import Tuple


class Block(Sprite):
    """
    A generic patch/agent. Has a Pixel_xy but not necessarily a RowCol. Has a Color.
    """
    def __init__(self, center_pixel: Pixel_xy, color=Color('black')):
        super().__init__()
        self.center_pixel = center_pixel
        self.rect = Rect((0, 0), (gui.PATCH_SIZE, gui.PATCH_SIZE))
        # noinspection PyTypeChecker
        sum_pixel: Pixel_xy = center_pixel + Pixel_xy((1, 1))
        assert isinstance(sum_pixel, Pixel_xy)
        self.rect.center = sum_pixel    # .as_tuple()
        self.image = Surface((self.rect.w, self.rect.h))
        self.color = self.base_color = color
        self.label = None
        self.font = Font(None, int(1.5*gui.BLOCK_SPACING()))
        self.agent_text_offset = int(1.5*gui.PATCH_SIZE)
        self.patch_text_offset = -int(1.0*gui.PATCH_SIZE)

    def distance_to_xy(self, xy: Pixel_xy):
        x_dist = self.center_pixel.x - xy.x
        y_dist = self.center_pixel.y - xy.y
        dist = sqrt(x_dist * x_dist + y_dist*y_dist)
        return dist
        
    def draw(self):
        if self.label:
            text = self.font.render(self.label, True, (0, 0, 0), (255, 255, 255))
            offset = self.patch_text_offset if isinstance(self, Patch) else self.agent_text_offset
            gui.SCREEN.blit(text, (self.rect.x + offset, self.rect.y + offset))
        gui.SCREEN.blit(self.image, self.rect)

    @staticmethod
    def get_gui_value(key):
        return World.THE_WORLD.get_gui_value(key)

    def set_color(self, color):
        self.color = color
        self.image.fill(color)

    @staticmethod
    def the_world():
        return World.THE_WORLD


class Patch(Block):
    def __init__(self, row_col: RowCol, color=Color('black')):
        super().__init__(row_col.patch_to_center_pixel(), color)
        self.row_col = row_col
        self.agents = None
        self._neighbors_4 = None
        self._neighbors_8 = None

    def __str__(self):
        class_name = utils.get_class_name(self)
        return f'{class_name}{(self.row_col.row, self.row_col.col)}'

    def add_agent(self, tur):
        self.agents.add(tur)

    def clear(self):
        self.agents = set()
        self.label = None
        self.set_color(self.base_color)

    def neighbors_4(self):
        if self._neighbors_4 is None:
            cardinal_deltas = ((-1, 0), (1, 0), (0, -1), (0, 1))
            self._neighbors_4 = self.neighbors(cardinal_deltas)
        return self._neighbors_4

    def neighbors_8(self):
        if self._neighbors_8 is None:
            all_deltas = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
            self._neighbors_8 = self.neighbors(all_deltas)
        return self._neighbors_8

    def neighbors(self, deltas):
        """
        The neighbors of this patch determined by the deltas.
        Note the addition of two RowCol objects to produce a new RowCol object: self.row_col + utils.RowCol(r, c).
        Wrap around is handled by RowCol. We then turn the RowCol object to a tuple to access the np.ndarray
        """
        # noinspection PyUnresolvedReferences
        neighbors = [self.the_world().patches_array[(self.row_col + RowCol((r, c))).wrap().as_int()]
                     for (r, c) in deltas]
        return neighbors

    def remove_agent(self, agent):
        self.agents.remove(agent)


class World:

    THE_WORLD = None

    def __init__(self, patch_class, agent_class):
        # wpb.THE_WORLD = self
        World.THE_WORLD = self

        self.event = None
        self.values = None

        self.ticks = 0

        self.patch_class = patch_class
        self.patches_array: np.ndarray = self.createpatches_array()
        # .flat is an iterator. Can't use it more than once.
        self.patches = list(self.patches_array.flat)

        self.agent_class = agent_class
        self.agents = set()

    def clear_all(self):
        self.agents = set()
        for patch in self.patches:   # .flat:
            patch.clear()

    def create_agents(self, nbr_agents):
        for _ in range(nbr_agents):
            self.agent_class()

    def create_ordered_agents(self, n):
        """Create n Agents with headings evenly spaced from 0 to 360"""
        for i in range(n):
            agent = self.agent_class()
            heading = i*360/n
            agent.set_heading(heading)

    def createpatches_array(self):
        # print('About to createpatches_array')
        patch_pseudo_array = [[self.patch_class(RowCol((r, c))) for c in range(gui.PATCH_COLS)]
                              for r in range(gui.PATCH_ROWS)]
        # print('Finished createpatches_array')
        patches_array = np.array(patch_pseudo_array)
        return patches_array

    def done(self):
        return False

    def draw(self):
        for patch in self.patches:   # .flat:.flat:
            patch.draw()

        for agent in self.agents:
            agent.draw()

    def final_thoughts(self):
        """ Add any final tests, data gathering, summarization, etc. here. """
        pass
        # Uncomment this code to see how well the caches work.
        # print()
        # for fn in [utils._heading_to_dxdy_int, utils._dx_int, utils._dy_int,
        #            utils.atan2_normalized, utils._cos_int, utils._sin_int]:
        #     if fn == utils.atan2:
        #         print()
        #     print(f'{str(fn.__wrapped__).split(" ")[1]}: {fn.cache_info()}')


    # @staticmethod
    def get_gui_event_values(self):
        return (self.event, self.values)

    def get_gui_value(self, key):
        value = self.values.get(key, None)
        return int(value) if isinstance(value, float) and value == int(value) else value

    def handle_event_and_values(self):
        pass

    def increment_ticks(self):
        self.ticks += 1

    def mouse_click(self, xy):
        pass

    def pixel_to_patch(self, xy: Tuple[int, int]):
        """
        Get the patch RowCol for this pixel
       """
        (x, y) = xy
        row_col: RowCol = Pixel_xy((x, y)).pixel_to_row_col()
        patch = self.patches_array[row_col.row, row_col.col]
        return patch

    def pixel_xy_to_patch(self, pixel_xy: Pixel_xy) -> Patch:
        """
        Get the patch RowCol for this pixel
       """
        row_col: RowCol = pixel_xy.pixel_to_row_col()
        patch = self.patches_array[row_col.row, row_col.col]
        return patch

    def reset_all(self):
        self.clear_all()
        self.reset_ticks()

    def reset_ticks(self):
        self.ticks = 0

    def save_event_and_values(self, event, values):
        self.event = event
        self.values = values

    # def save_event_and_values_and_handle_them(self, event, values):
    #     self.save_event_and_values(event, values)
    #     self.handle_events()

    # def save_values_and_setup(self, event, values):
    #     self.save_event_and_values(event, values)
    #     self.setup()

    def setup(self):
        pass

    # def save_values_and_step(self, event, values):
    #     self.save_event_and_values(event, values)
    #     self.step()

    def step(self):
        """
        Update the world. Override for each world
        """
        pass

    @staticmethod
    def the_world():
        return World.THE_WORLD
