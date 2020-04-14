from itertools import cycle
from math import floor, ceil
from random import random, uniform, randrange, randint

from core.agent import Agent
from core.pairs import Velocity
from core.sim_engine import SimEngine
from core.world_patch_block import World, Patch
from core.pairs import Pixel_xy, RowCol
from pygame.color import Color


class Commuter(Agent):
    def __init__(self, b_t, **kwargs):
        self.passed_tr = False
        self.passed_bl = False
        self.in_middle = False
        self.ticks_here = 0
        self.route = 0
        self.birth_tick = b_t
        kwargs['color'] = Color("red")

        super().__init__(**kwargs)

    def move(self, initial_speed, move_by_delay):
        if move_by_delay:
            patch = self.current_patch()
            if self.route == 1:
                patch_ahead = World.patches_array[patch.row + 1, patch.col]
            else:
                patch_ahead = World.patches_array[patch.row, patch.col + 1]

            self.move_to_patch(patch_ahead)
            self.ticks_here = 1

        else:
            if self.current_patch().color == Color("green"):
                speed = initial_speed
            else:
                speed = (self.current_patch().color.b / 127)
                if speed <= 1:
                    speed = 1
            self.forward(speed)

    def set_route(self, r):
        self.route = r

    def follow_route(self):
        if self.route == 1:
            self.face_xy(World.bot_left.center_pixel)
        else:
            self.face_xy(World.top_right.center_pixel)

    def middle(self):
        if self.route == 2:
            return True

    def __str__(self):
        return f'FLN-{self.id}'


class Road_Patch(Patch):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = 0
        self.base_delay = 0
        self.road_type = 0
        self.last_here = 0

    def determine_congestion(self, spawn_rate, highway, move_by_delay):
        if self.last_here == 0:
            self.delay = int(self.base_delay/2)
        else:
            self.delay = floor(((250/spawn_rate)/(World.ticks-self.last_here+1))*self.base_delay)
        g = 255 + floor(255 * (0.5 - self.delay / self.base_delay))
        if g < 100:
            g = 100
        if g > 255:
            g = 255

        if self.delay > 10:
            self.delay = 10

        if move_by_delay:
            print(g)
            self.set_color(Color(g, g, g))
        else:
            if self in highway.top_road:
                prev_patch = highway.top_road[self.col - 12]
            else:
                prev_patch = highway.bottom_road[self.col - 12]
            prev_patch.set_color(Color(g, g, g))


class Highway:
    def __init__(self, t_r, b_r, l_r, r_r, m_r, o_r):
        self.top_road = t_r
        self.bottom_road = b_r
        self.left_road = l_r
        self.right_road = r_r
        self.outer_road = o_r
        self.middle_road = m_r
        self.middle_prev = True
        self.delay_prev = True

    def create_road(self):
        # outer roads
        for arr in self.outer_road:
            for patch in arr:
                patch.set_color(Color("orange"))
                patch.road_type = 0
        # middle road
        for patch in self.middle_road:
            patch.set_color(Color("yellow"))
            patch.road_type = 0
            patch.delay = 0
        # top road
        for patch in self.top_road:
            patch.set_color(Color("white"))
            patch.road_type = 1
            patch.delay = 5
            patch.base_delay = 10
        # bottom road
        for patch in self.bottom_road:
            patch.set_color(Color("white"))
            patch.road_type = 1
            patch.delay = 5
            patch.base_delay = 10
        # left road
        for patch in self.left_road:
            patch.set_color(Color(100, 100, 100))
            patch.road_type = 0
            patch.delay = 10
        # right road
        for patch in self.right_road:
            patch.set_color(Color(100, 100, 100))
            patch.road_type = 0
            patch.delay = 10

    def check_middle(self, middle_on, delay_on):
        if middle_on != self.middle_prev:
            if middle_on:
                for patch in self.middle_road:
                    patch.set_color(Color("yellow"))
                self.middle_prev = middle_on
                self.check_delay(middle_on, delay_on)
            else:
                for patch in self.middle_road:
                    patch.set_color(Color("orange"))
                    self.middle_prev = middle_on
                self.check_delay(middle_on, delay_on)

    def check_delay(self, middle_on, delay_on):
        if delay_on != self.delay_prev:
            self.create_road()
            self.delay_prev = delay_on
            self.check_middle(middle_on, delay_on)

class Commuter_World(World):
    top_left = None
    top_right = None
    bot_left = None
    bot_right = None
    despawn_list = None

    top_road = None
    bottom_road = None
    left_road = None
    right_road = None
    highway = None

    travel_time = None
    top = None
    bot = None
    middle = None
    spawn_time = None
    avg = None
    cars_spawned = None

    num_top = None
    num_bot = None
    num_mid = None

    def __init__(self, *args, **kwargs):
        self.patch_class = Road_Patch
        super().__init__(*args, **kwargs)

    @staticmethod
    def setup_roads():
        all_patches = World.patches_array

        World.top_road = all_patches[10, 11:60]
        World.bottom_road = all_patches[60, 11:60]
        World.left_road = all_patches[11:60, 10]
        World.right_road = all_patches[11:60, 60]
        # the outer road is concatenated in this order: top -> left -> right -> bottom
        outer_road = [all_patches[9, 9:62]] + [all_patches[11, 11:58]] + \
                     [all_patches[10:62, 9]] + [all_patches[11:58, 11]] + \
                     [all_patches[13:60, 59]] + [all_patches[10:62, 61]] + \
                     [all_patches[59, 13:60]] + [all_patches[61, 10:61]]

        middle_road = []
        for j in range(11, 60):
            outer_road.append([World.patches_array[j - 2, 70 - j]])
            outer_road.append([World.patches_array[j + 2, 70 - j]])
            middle_road.append(World.patches_array[j - 1, 70 - j])
            middle_road.append(World.patches_array[j, 70 - j])
            middle_road.append(World.patches_array[j + 1, 70 - j])

        # Create all the roads
        World.highway = Highway(World.top_road, World.bottom_road,
                                World.left_road, World.right_road,
                                middle_road, outer_road)
        World.highway.create_road()

        # Make top_left patch
        World.top_left = World.patches_array[10, 10]
        World.top_left.set_color(Color("green"))

        # Make top_right patch
        World.top_right = World.patches_array[10, 60]
        World.top_right.set_color(Color("blue"))

        # Make bot_left patch
        World.bot_left = World.patches_array[60, 10]
        World.bot_left.set_color(Color("blue"))

        # Make bot_right patch
        World.bot_right = World.patches_array[60, 60]
        World.bot_right.set_color(Color("red"))

    def setup(self):
        self.setup_roads()

        World.travel_time = 0
        World.top = 0
        World.bot = 0
        World.middle = 0
        World.spawn_time = 0
        World.avg = 0
        World.cars_spawned = 0
        World.despawn_list = []
        World.num_top = 0
        World.num_bot = 0
        World.num_mid = 0

    def step(self):
        """
        Update the world by moving the agents.
        """
        spawn_rate = SimEngine.gui_get('spawn rate')
        middle_on = SimEngine.gui_get("middle_on")
        delay_on = SimEngine.gui_get("delay")

        # check if the checkboxes have changed (Middle On? and Move by Delay?)
        World.highway.check_delay(middle_on, delay_on)
        World.highway.check_middle(middle_on, delay_on)

        # set the route count of each route to 0
        World.num_top = 0
        World.num_bot = 0
        World.num_mid = 0

        # move the computers
        self.move_commuters()

        # set the patch color and patch delay
        for patch in World.patches:
            if patch.road_type == 1:
                patch.determine_congestion(spawn_rate, World.highway, delay_on)

        # spawn agents
        self.spawn_commuter()

    def new_route(self):
        b = SimEngine.gui_get('best')
        if b == 'Best Known /w Random Dev':
            route = self.best_random_route()
        elif b == 'Empirical Analytical':
            route = self.analytical_route()
        elif b == 'Probabilistic Greedy':
            route = self.probablisitic_greedy_route()
        else:
            route = 0
        return route

    def spawn_commuter(self):
        spawn_rate = SimEngine.gui_get('spawn rate')
        if World.spawn_time > (250 / spawn_rate):
            World.cars_spawned = World.cars_spawned + 1
            a = Commuter(World.ticks, scale=1)
            a.move_to_patch(World.top_left)
            a.set_route(self.new_route())
            a.follow_route()
            World.spawn_time = 0
        else:
            World.spawn_time = World.spawn_time + 1

    def end_commute(self, agent):
        ...

    def move_commuters(self):
        delay_on = SimEngine.gui_get("delay")

        # delete agents that finished route
        for agent in World.despawn_list:
            if agent in World.agents:
                World.agents.remove(agent)

        for agent in World.agents:

            curr_patch = agent.current_patch()
            if not delay_on:
                curr_patch.delay = -1
            if agent.ticks_here > curr_patch.delay:
                curr_patch.last_here = World.ticks
                if agent.current_patch() is World.top_right:
                    World.despawn_list.append(agent)
                if agent.current_patch() is World.bot_left:
                    World.despawn_list.append(agent)
                agent.move(1, delay_on)
            else:
                agent.ticks_here = agent.ticks_here + 1


    def probablisitic_greedy_route(self):
        middle_on = SimEngine.gui_get("middle_on")
        randomness = SimEngine.gui_get("randomness")

        if middle_on:
            if World.middle == 0 or World.bot == 0 or World.top == 0:
                return randint(0, 2)

            t_dif = 2 - World.top
            if t_dif < 0:
                t_dif = 0
            t_dif = t_dif**(randomness/10)

            b_dif = 2 - World.bot
            if b_dif < 0:
                b_dif = 0
            b_dif = b_dif ** (randomness / 10)

            m_dif = 2 - World.top
            if m_dif < 0:
                m_dif = 0
            m_dif = m_dif ** (randomness / 10)

            if not t_dif + b_dif + m_dif == 0:
                sigma1 = t_dif / (t_dif + b_dif + m_dif)
                sigma2 = b_dif / (t_dif + b_dif + m_dif)
            else:
                sigma1 = 0.33
                sigma2 = 0.33

            split1 = 1000 * sigma1
            split2 = 1000 * (sigma1 + sigma2)
            rand = random() * 1000
            if rand < split1:
                return 0
            else:
                if rand < split2:
                    return 1
                else:
                    return 2
        else:
            if World.top == 0 or World.bot == 0:
                return randint(0, 1)

            t_dif = (2-World.top)**(randomness/10)
            b_dif = (2-World.bot)**(randomness/10)
            sigma = t_dif / (t_dif + b_dif)
            split = 1000 * sigma
            if (random() * 1000) < split:
                return 0
            else:
                return 1

    def best_random_route(self):
        return 1

    def analytical_route(self):
        return 0






# ############################################## Define GUI ############################################## #
import PySimpleGUI as sg

gui_left_upper = [[sg.Text('Spawn Rate', pad=((0, 5), (20, 0))),
                   sg.Slider(key='spawn rate', range=(1, 10), default_value=10,
                             orientation='horizontal', size=(10, 20))],

                  [sg.Text('Smoothing', pad=((0, 5), (20, 0))),
                   sg.Slider(key='smoothing', range=(1, 10), default_value=10,
                             orientation='horizontal', size=(10, 20))],

                  [sg.Text('Randomness', pad=((0, 5), (20, 0))),
                   sg.Slider(key='randomness', range=(0, 100), default_value=10,
                             orientation='horizontal', size=(10, 20))],

                  [sg.Combo(['Best Known /w Random Dev', 'Empirical Analytical', 'Probabilistic Greedy'],
                            default_value='Probabilistic Greedy', pad=((0, 5), (20, 0)), key='best')],

                  [sg.Checkbox("Middle On?", key='middle_on', default=True, pad=((20, 0), (20, 0)))],

                  [sg.Checkbox("Move by Delay?", key='delay', default=True, pad=((20, 0), (20, 0)))]
                  ]

if __name__ == "__main__":
    from core.agent import PyLogo

    PyLogo(Commuter_World, 'Paradox', gui_left_upper, agent_class=Commuter, patch_class=Road_Patch,
           bounce=True, patch_size=9,
           board_rows_cols=(71, 71))
