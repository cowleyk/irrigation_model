from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..irrigation_model_calculations import IrrigationCalculations
from ..irrigation_model_block import IrrigationModel
import unittest
from unittest.mock import patch, ANY
from datetime import date


class TestIrrigationModel(NIOBlockTestCase):
    input_signal = {'user_root_zones': [1, 2],
                     'sm_units': {'key1': 'val1'},
                     'fc_high': 0.96,
                     'fc_low': 0.69,
                     'last_irrigation_gpp': 6,
                     'last_irrigation_date': 'datetime',
                     'current_date': 'datetime2',}
    vineyard_constants = {
        'all_zones': ['4', '8', '16', '24', '32', '40'],
        'multiplier': 1.3,
        'vineyard_cfgs': {'key2': 'val2'},
    }
    # @patch('blocks.irrigation_model.irrigation_model_block.IrrigationBase')
    # @patch.object(IrrigationBase)
    def test_process_signals(self):
        """Signals pass through block unmodified."""

        with patch(IrrigationModel.__module__ + '.IrrigationCalculations') as mixin:
            self.maxDiff = None
            blk = IrrigationModel()
            self.configure_block(blk, {'user_root_zones': '{{$user_root_zones}}',
                                       'sm_units': '{{$sm_units}}',
                                       'fc_high': '{{$fc_high}}',
                                       'fc_low': '{{$fc_low}}',
                                       'last_irrigation_gpp': \
                                           '{{$last_irrigation_gpp}}',
                                       'last_irrigation_date': \
                                           '{{$last_irrigation_date}}',
                                       'current_date': '{{$current_date}}',
                                       'vineyard_cfgs': self.vineyard_constants['vineyard_cfgs'],})
            blk.start()
            blk.process_signals([Signal(self.input_signal)])

            mixin.calc_percent_fc_average_root_zone.assert_called_once_with(
                        self.input_signal['user_root_zones'],
                        self.input_signal['sm_units'],
                        self.vineyard_constants['vineyard_cfgs'])
            mixin.calc_percent_awc_average_root_zone.assert_called_once_with(
                        self.input_signal['user_root_zones'],
                        self.input_signal['sm_units'],
                        self.vineyard_constants['vineyard_cfgs'])
            mixin.calc_gpp_required_to_reach_fc_goal.assert_called_once_with(
                        self.input_signal['user_root_zones'],
                        self.input_signal['sm_units'],
                        self.input_signal['fc_high'],
                        self.input_signal['last_irrigation_gpp'],
                        self.vineyard_constants['all_zones'],
                        self.vineyard_constants['vineyard_cfgs'],
                        self.vineyard_constants['multiplier'])
            mixin.calc_average_drawdown_per_day.assert_called_once_with(
                        self.input_signal['sm_units'],
                        self.input_signal['last_irrigation_date'],
                        self.input_signal['current_date'])
            mixin.calc_est_days_until_irr.assert_called_once_with(
                        self.input_signal['user_root_zones'],
                        self.input_signal['sm_units'],
                        self.input_signal['fc_low'],
                        self.input_signal['last_irrigation_date'],
                        self.input_signal['current_date'],
                        self.vineyard_constants['vineyard_cfgs'])
            blk.stop()
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
                {
                    'percent_of_FC': ANY,
                    'percent_of_AWC': ANY,
                    'GPP_required_to_reach_FC_high': ANY,
                    'avg_draw_down_per_day': ANY,
                    'est_days_to_next_irrigation': ANY,
                },
                self.last_notified[DEFAULT_TERMINAL][0].to_dict())


class TestIrrigationCalculations(unittest.TestCase):
    sm_units = {
        '4': {
            'last_irrigated': 55.0,
            '24hrs_post_irrigation': 64.0,
            'current': 53.0,
        },
        '8': {
            'last_irrigated': 58.0,
            '24hrs_post_irrigation': 66.0,
            'current': 57.0,
        },
        '16': {
            'last_irrigated': 62.0,
            '24hrs_post_irrigation': 66.0,
            'current': 60.0,
        },
        '24': {
            'last_irrigated': 68.0,
            '24hrs_post_irrigation': 73.0,
            'current': 65.0,
        },
        '32': {
            'last_irrigated': 68.0,
            '24hrs_post_irrigation': 70.0,
            'current': 65.0,
        },
        '40': {
            'last_irrigated': 62.0,
            '24hrs_post_irrigation': 62.0,
            'current': 60.0,
        },
    }
    fc_high = 0.95
    fc_low = 0.85
    user_root_zones = ['16', '24', '32']
    last_irrigation_gpp = 8
    last_irrigation_date = date(2017, 5, 5)
    current_date = date(2017, 5, 20)
    vineyard_cfgs = {
        '4': {
            'SaturationPoint': 69.0,
            'FieldCapacityPoint': 64.0,
            'PermWiltingPoint': 41.0,
        },
        '8': {
            'SaturationPoint': 71.0,
            'FieldCapacityPoint': 66.0,
            'PermWiltingPoint': 42.0,
        },
        '16': {
            'SaturationPoint': 69.0,
            'FieldCapacityPoint': 66.0,
            'PermWiltingPoint': 42.0,
        },
        '24': {
            'SaturationPoint': 74.0,
            'FieldCapacityPoint': 73.0,
            'PermWiltingPoint': 48.0,
        },
        '32': {
            'SaturationPoint': 70.0,
            'FieldCapacityPoint': 70.0,
            'PermWiltingPoint': 45.0,
        },
        '40': {
            'SaturationPoint': 64.0,
            'FieldCapacityPoint': 64.0,
            'PermWiltingPoint': 41.0,
        },
    }
    all_zones = ['4', '8', '16', '24', '32', '40']
    multiplier = 1.3

    def test_calc_percent_fc_average_root_zone(self):
        rounded = round(
            IrrigationCalculations.calc_percent_fc_average_root_zone(
                self.user_root_zones, self.sm_units, self.vineyard_cfgs),
            2)
        self.assertEqual(rounded, 0.91)

    def test_calc_percent_awc_average_root_zone(self):
        rounded = round(
            IrrigationCalculations.calc_percent_awc_average_root_zone(
                self.user_root_zones, self.sm_units, self.vineyard_cfgs),
            2)
        self.assertEqual(rounded, 0.74)

    def test_calc_gpp_required_to_reach_fc_goal(self):
        rounded = round(
            IrrigationCalculations.calc_gpp_required_to_reach_fc_goal(
                self.user_root_zones, self.sm_units,
                self.fc_high, self.last_irrigation_gpp,
                self.all_zones, self.vineyard_cfgs,
                self.multiplier),
            2)
        self.assertEqual(rounded, 3.18)

    def test_calc_average_drawdown_per_day(self):
        rounded = round(
            IrrigationCalculations.calc_average_drawdown_per_day(
                self.sm_units, self.last_irrigation_date, self.current_date),
            2)
        self.assertEqual(rounded, -1.88)

    def test_calc_est_days_until_irr(self):
        rounded = round(
            IrrigationCalculations.calc_est_days_until_irr(
                self.user_root_zones, self.sm_units,
                self.fc_low, self.last_irrigation_date,
                self.current_date, self.vineyard_cfgs),
            2)
        self.assertEqual(rounded, 6.57)
