from nio.properties import VersionProperty, Property
from nio.signal.base import Signal
from .irrigation_model_calculations import IrrigationCalculations
from nio.block.base import Block


class IrrigationModel(Block):
    # TODO: ADD EnrichSignal mixin

    version = VersionProperty('0.1.0')

    # User configs from front end
    user_root_zones = Property(title='Root Zones', default='{{ [16, 24, 32] }}')
    fc_high = Property(title='% FC Goal (root zone)', default='0.95')
    fc_low = Property(title='% FC min (root zone)', default='0.85')

    # From n.io query to database
    sm_units = Property(title='SM Data', default='{{ {} }}')
    last_irrigation_date = Property(title='Date of Last Irrigation',
                                    default='')
    current_date = Property(title='Current Date',
                            default='{{ datetime.date.today() }}',
                            visible=False)
    last_irrigation_gpp = Property(title='Last Irrigation\'s GPP',
                                   default='{{ 0 }}')
    # One-time configs
    vineyard_cfgs = Property(title='Vineyard Depths Configuration',
                             default='{{ {} }}')
    multiplier_signal = Property(title='Multiplier',
                                 default='{{ 1.3 }}')
    all_zones = Property(title='All Zones',
                         default='{{ ["4", "8", "16", "24", "32", "40"] }}')

    def process_signals(self, signals):
        for signal in signals:
            vineyard_cfgs = self.vineyard_cfgs(signal)
            multiplier = float(self.multiplier_signal(signal))
            all_zones = self.all_zones(signal)
            last_irrigation_date = self.last_irrigation_date(signal)
            current_date = self.current_date(signal)
            last_irrigation_gpp = float(self.last_irrigation_gpp(signal))
            fc_high = float(self.fc_high(signal))
            fc_low = float(self.fc_low(signal))
            sm_units = self.sm_units(signal)
            user_root_zones = self.user_root_zones(signal)
            perc_fc_in_root_zone = \
                IrrigationCalculations.calc_percent_fc_average_root_zone(
                    user_root_zones, sm_units, vineyard_cfgs)
            perc_awc_in_root_zone = \
                IrrigationCalculations.calc_percent_awc_average_root_zone(
                    user_root_zones, sm_units, vineyard_cfgs)
            gpp_required = \
                IrrigationCalculations.calc_gpp_required_to_reach_fc_goal(
                    user_root_zones, sm_units, fc_high, last_irrigation_gpp,
                    all_zones, vineyard_cfgs, multiplier)
            avg_draw_down = \
                IrrigationCalculations.calc_average_drawdown_per_day(
                    sm_units, last_irrigation_date, current_date)
            est_days_until_irr = \
                IrrigationCalculations.calc_est_days_until_irr(
                    user_root_zones, sm_units, fc_low,
                    last_irrigation_date, current_date, vineyard_cfgs)

        calcd_signal = [Signal({
            'percent_of_FC': perc_fc_in_root_zone,
            'percent_of_AWC': perc_awc_in_root_zone,
            'GPP_required_to_reach_FC_high': gpp_required,
            'avg_draw_down_per_day': avg_draw_down,
            'est_days_to_next_irrigation': est_days_until_irr,
        })]
        self.notify_signals(calcd_signal)
