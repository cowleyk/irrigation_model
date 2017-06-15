from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..irrigation_model_block import IrrigationModel, IrrigationCalculations
from unittest.mock import patch, MagicMock, ANY


class TestIrrigationModel(NIOBlockTestCase):

    @patch('blocks.irrigation_model.irrigation_model_block.IrrigationCalculations')
    def test_process_signals(self, mock_model):
    # def test_process_signals(self):
        """Signals pass through block unmodified."""
        blk = IrrigationModel()
        self.configure_block(blk, {'user_root_zones': '{{$user_root_zones}}',
                                   'sm_units': '{{$sm_units}}',
                                   'fc_high': '{{$fc_high}}',
                                   'fc_low': '{{$fc_low}}',
                                   'last_irrigation_gpp': '{{$last_irrigation_gpp}}',
                                   'last_irrigation_date': '{{$last_irrigation_date}}'})
        blk.start()
        blk.process_signals([Signal({'user_root_zones': [8, 16],
                                     'sm_units': {1: 1},
                                     'fc_high': 0.96,
                                     'fc_low': 0.69,
                                     'last_irrigation_gpp': 6,
                                     'last_irrigation_date': 'datetime'})])
        blk.stop()
        mock_model._calc_percent_fc_average_root_zone.assert_called_once_with(
                    [8, 16], {1: 1})
        mock_model._calc_percent_awc_average_root_zone.assert_called_once_with(
                    [8, 16], {1: 1})
        mock_model._calc_gpp_required_to_reach_fc_goal.assert_called_once_with(
                    [8, 16], {1: 1}, 0.96, 6)
        mock_model._calc_average_drawdown_per_day.assert_called_once_with(
                    {1: 1}, 'datetime')
        mock_model._calc_est_days_until_irr.assert_called_once_with(
                    [8, 16], {1: 1}, 0.69, 'datetime')




        self.assert_num_signals_notified(1)
        print(self.last_notified[DEFAULT_TERMINAL][0].to_dict())
        # self.assertDictEqual(
        #         self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
        #         {
        #             'sm_units': ANY,
        #             'user_root_zones': ANY,
        #             'percent_of_FC': ANY,
        #             'percent_of_AWC': ANY,
        #             'GPP_required_to_reach_FC_high': ANY,
        #             'avg_draw_down_per_day': ANY,
        #             'est_days_to_next_irrigation': ANY,
        #         })

    # JUST WANT TO TEST FUNCTIONS ARE CALLED IN THE CORRECT ORDER
    # Eg;
    # mock_model._calc_percent_fc_user_zones.assert_called_once_with('nonsense')
