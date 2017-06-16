from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..irrigation_model_block import IrrigationModel, IrrigationCalculations
import unittest
from unittest.mock import patch, MagicMock, ANY
from datetime import date


class TestIrrigationModel(NIOBlockTestCase):

    @patch('blocks.irrigation_model.irrigation_model_block.'
           'IrrigationCalculations')
    def test_process_signals(self, mock_model):
        """Signals pass through block unmodified."""

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
                                   'vineyard_cfgs': '{{ $vineyard_cfgs }}'})
        blk.start()
        blk.process_signals([Signal({'user_root_zones': [8, 16],
                                     'sm_units': {1: 1},
                                     'fc_high': 0.96,
                                     'fc_low': 0.69,
                                     'last_irrigation_gpp': 6,
                                     'last_irrigation_date': 'datetime',
                                     'current_date': 'datetime2',
                                     'vineyard_cfgs': {2: 2},})])
        blk.stop()
        mock_model._calc_percent_fc_average_root_zone.assert_called_once_with(
                    [8, 16], {1: 1}, {2: 2})
        mock_model._calc_percent_awc_average_root_zone.assert_called_once_with(
                    [8, 16], {1: 1}, {2: 2})
        mock_model._calc_gpp_required_to_reach_fc_goal.assert_called_once_with(
                    [8, 16], {1: 1}, 0.96, 6, [4, 8, 16, 24, 32, 40], {2: 2}, 1.3)
        mock_model._calc_average_drawdown_per_day.assert_called_once_with(
                    {1: 1}, 'datetime', 'datetime2')
        mock_model._calc_est_days_until_irr.assert_called_once_with(
                    [8, 16], {1: 1}, 0.69, 'datetime', 'datetime2', {2: 2})

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
    irrigation_calculations = IrrigationCalculations()
    def test_calc_percent_fc_average_root_zone(self):
        rounded = round(
            self.irrigation_calculations._calc_percent_fc_average_root_zone(
                user_root_zones, sm_units, vineyard_cfgs),
            2)
        self.assertEqual(rounded, 0.91)

    def test_calc_percent_awc_average_root_zone(self):
        rounded = round(
            self.irrigation_calculations._calc_percent_awc_average_root_zone(
                user_root_zones, sm_units, vineyard_cfgs),
            2)
        self.assertEqual(rounded, 0.74)

    def test_calc_gpp_required_to_reach_fc_goal(self):
        rounded = round(
            self.irrigation_calculations._calc_gpp_required_to_reach_fc_goal(
                user_root_zones, sm_units,
                fc_high, last_irrigation_gpp,
                all_zones, vineyard_cfgs,
                multiplier),
            2)
        self.assertEqual(rounded, 3.18)

    def test_calc_average_drawdown_per_day(self):
    # @patch('datetime.date')
    # def test_calc_average_drawdown_per_day(self, mock_date):
        # mock_date.today.return_value = date(2017, 5, 20)
        rounded = round(
            self.irrigation_calculations._calc_average_drawdown_per_day(
                sm_units, last_irrigation_date, current_date),
            2)
        self.assertEqual(rounded, -1.88)

    def test_calc_est_days_until_irr(self):
        rounded = round(
            self.irrigation_calculations._calc_est_days_until_irr(
                user_root_zones, sm_units,
                fc_low, last_irrigation_date,
                current_date, vineyard_cfgs),
            2)
        self.assertEqual(rounded, 6.57)

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