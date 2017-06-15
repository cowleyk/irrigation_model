from nio.block.base import Block
from nio.properties import VersionProperty
from nio.properties.string import StringProperty
from nio.properties import Property, FloatProperty
from nio.signal.base import Signal


from datetime import date


class IrrigationModel(Block):

    version = VersionProperty('0.1.0')

    # User configs from front end
    user_root_zones = Property(title='Root Zones', default='[16, 24, 32]')
    fc_high = FloatProperty(title='% FC Goal (root zone)', default='0.95')
    fc_low = FloatProperty(title='% FC min (root zone)', default='0.85')

    # From n.io query to database
    sm_units = Property(title='SM Data', default='{}')
    last_irrigation_date = Property(title='Date of Last Irrigation',
                                    default='')
    last_irrigation_gpp = FloatProperty(title='Last Irrigation\'s GPP',
                                    default='0')
    # One-time configs
    vineyard_cfgs_signal = Property(title='Attribute Title',
                                   default='{}')
    multiplier_signal = FloatProperty(title='Multiplier',
                                      default='1')
    all_zones = Property(title='All Zones', default='[4, 8, 16, 24, 32, 40]')

    def process_signals(self, signals):
        calcd_signal = []
        # TODO: FOCUS ON GPP REC
        for signal in signals:
            vineyard_cfgs = self.vineyard_cfgs_signal(signal)
            multiplier = self.multiplier_signal(signal)
            last_irrigation_date = self.last_irrigation_date(signal)
            last_irrigation_gpp = self.last_irrigation_gpp(signal)
            fc_high = self.fc_high(signal)
            fc_low = self.fc_low(signal)
            sm_units = self.sm_units(signal)
            user_root_zones = self.user_root_zones(signal)
            perc_fc_in_root_zone = \
                IrrigationCalculations._calc_percent_fc_average_root_zone(
                    user_root_zones, sm_units)
            perc_awc_in_root_zone = \
                IrrigationCalculations._calc_percent_awc_average_root_zone(
                    user_root_zones, sm_units)
            gpp_required = \
                IrrigationCalculations._calc_gpp_required_to_reach_fc_goal(
                    user_root_zones, sm_units, fc_high, last_irrigation_gpp)
            avg_draw_down = \
                IrrigationCalculations._calc_average_drawdown_per_day(
                    sm_units, last_irrigation_date)
            est_days_until_irr = \
                IrrigationCalculations._calc_est_days_until_irr(
                    user_root_zones, sm_units, fc_low, last_irrigation_date)

        calcd_signal = [Signal({
            'sm_units': sm_units,
            'user_root_zones': user_root_zones,
            'percent_of_FC': perc_fc_in_root_zone,
            'percent_of_AWC': perc_awc_in_root_zone,
            'GPP_required_to_reach_FC_high': gpp_required,
            'avg_draw_down_per_day': avg_draw_down,
            'est_days_to_next_irrigation': est_days_until_irr,
        })]
        self.notify_signals(calcd_signal)


class IrrigationCalculations():

    def _calc_percent_fc_user_zones(self, user_root_zones, sm_units):
        # current SM units/Field capacity points
        percent_fc = []
        for zone in user_root_zones:
            percent_fc.append(sm_units[zone]['current']
                              / vineyard_cfgs[zone]['FieldCapacityPoint'])
        return percent_fc

    def _calc_percent_fc_average_root_zone(self, user_root_zones, sm_units):
        # average of fc
        percent_fc_zones = self._calc_percent_fc_user_zones(user_root_zones,
                                                      sm_units)
        fc_total = 0
        for zone in percent_fc_zones:
            fc_total = fc_total + zone
        return fc_total / len(user_root_zones)

    def _calc_percent_awc_user_zones(self, user_root_zones, sm_units):
        # (current SM units - perm wilting point)/(field cap points - perm wilting point)
        percent_awc = []
        for zone in user_root_zones:
            percent_awc.append(
                (sm_units[zone]['current']
                - vineyard_cfgs[zone]['PermWiltingPoint'])
                / (vineyard_cfgs[zone]['FieldCapacityPoint']
                - vineyard_cfgs[zone]['PermWiltingPoint']))
        return percent_awc

    def _calc_percent_awc_average_root_zone(self, user_root_zones, sm_units):
        # average of awc
        percent_awc_zones = self._calc_percent_awc_user_zones(user_root_zones,
                                                        sm_units)
        awc_total = 0
        for zone in percent_awc_zones:
            awc_total = awc_total + zone
        return awc_total / len(user_root_zones)

    # ~~~~~~~~~~~~~~~~~~~
    # Gallons to Apply to Reach Target FC in Root Zone

    def _zones_above_user_input(self, user_root_zones):
        zones_above = []
        for zone in all_zones:
            if zone not in user_root_zones and zone < min(user_root_zones):
                zones_above.append(zone)
        return zones_above

    def _calc_sm_deficit_sp_above_user_zones(self, user_root_zones, sm_units):
        # sum(current SM units) - sum(saturation pts)
        zones_above = self._zones_above_user_input(user_root_zones)
        sm_units_sum = 0
        saturation_point_sum = 0
        for zone in zones_above:
            sm_units_sum = sm_units_sum + sm_units[zone]['current']
            saturation_point_sum = saturation_point_sum \
                                   + vineyard_cfgs[zone]['SaturationPoint']
        return sm_units_sum - saturation_point_sum

    def _calc_sm_deficit_fc_above_user_zones(self, user_root_zones, sm_units):
        # sum(current SM units) - sum(fc pts)
        zones_above = self._zones_above_user_input(user_root_zones)
        sm_units_sum = 0
        fc_point_sum = 0
        for zone in zones_above:
            sm_units_sum = sm_units_sum + sm_units[zone]['current']
            fc_point_sum = fc_point_sum \
                           + vineyard_cfgs[zone]['FieldCapacityPoint']
        return sm_units_sum - fc_point_sum

    def _calc_excess_sm_units_above_user_zones(self, user_root_zones, sm_units):
        return self._calc_sm_deficit_sp_above_user_zones(user_root_zones,
                                                        sm_units) \
               - self._calc_sm_deficit_fc_above_user_zones(user_root_zones,
                                                        sm_units)

    def _calc_sm_deficit_user_zones(self, user_root_zones, sm_units, fc_high):
        # sum(current SM units) - [sum(fc points) * fc high]
        sm_units_sum = 0
        fc_points_sum = 0
        for zone in user_root_zones:
            sm_units_sum = sm_units_sum + sm_units[zone]['current']
            fc_points_sum = fc_points_sum + vineyard_cfgs[zone][
                'FieldCapacityPoint']
        return sm_units_sum - (fc_points_sum * fc_high)

    def _calc_required_sm_increase_for_fc_high(self, user_root_zones, sm_units,
                                              fc_high):
        a = self._calc_sm_deficit_fc_above_user_zones(user_root_zones, sm_units)
        b = self._calc_sm_deficit_user_zones(user_root_zones, sm_units,
                                       fc_high) * multiplier
        return a + b

    def _calc_absorption_rate(self, sm_units, last_irrigation_gpp):
        # [sum(all sm units of 24hr post) - sum(all sm units start last)] / last irrigation gpp
        post_irrigation_sum = 0
        last_irrigated_sum = 0
        for zone in sm_units:
            post_irrigation_sum = post_irrigation_sum + sm_units[zone][
                '24hrs_post_irrigation']
            last_irrigated_sum = last_irrigated_sum + sm_units[zone][
                'last_irrigated']
        return (post_irrigation_sum - last_irrigated_sum) / last_irrigation_gpp

    def _calc_gpp_required_to_reach_fc_goal(self, user_root_zones,
                                            sm_units, fc_high,
                                            last_irrigation_gpp):
        if self._calc_sm_deficit_user_zones(user_root_zones,
                                            sm_units, fc_high) < 0:
            return abs(
                self._calc_required_sm_increase_for_fc_high(user_root_zones,
                                                            sm_units, fc_high)
                / self._calc_absorption_rate(sm_units, last_irrigation_gpp))
        else:
            return 0

    # ~~~~~~~~~~~~~~~~~~~
    # Days Until Required Irrigation

    def _calc_total_draw_down_since_last_irrigation(self, sm_units):
        evaporation_estimates = {'4': 1, '8': 0.2}
        change_in_sm_units_exclude_evaporation = []
        for zone in sm_units:
            change_in_sm_units = sm_units[zone]['current'] - sm_units[zone][
                '24hrs_post_irrigation']
            evaporation = evaporation_estimates.get(zone, 0)
            change_in_sm_units_exclude_evaporation.append(
                change_in_sm_units - (change_in_sm_units * evaporation))
        return sum(change_in_sm_units_exclude_evaporation)

    def _calc_average_drawdown_per_day(self, sm_units, last_irrigation_date):
        total_draw_down = self._calc_total_draw_down_since_last_irrigation(sm_units)
        return total_draw_down / ((date.today() - last_irrigation_date).days)

    def _calc_sm_draw_down_to_target_irr_percent(self, user_root_zones, sm_units,
                                                fc_low):
        current_sm_sum = 0
        fc_point_sum = 0
        for zone in user_root_zones:
            current_sm_sum = current_sm_sum + sm_units[zone]['current']
            fc_point_sum = fc_point_sum + vineyard_cfgs[zone][
                'FieldCapacityPoint']
        fc_point_sum_fc_low = fc_point_sum * fc_low
        return fc_point_sum_fc_low - current_sm_sum

    def _calc_est_days_until_irr(self, user_root_zones, sm_units, fc_low,
                                last_irrigation_date):
        return self._calc_sm_draw_down_to_target_irr_percent(user_root_zones,
                                                       sm_units,
                                                       fc_low) / self._calc_average_drawdown_per_day(
            sm_units, last_irrigation_date)

# vineyard_cfgs = {
#     '4': {
#         'SaturationPoint': 69.0,
#         'FieldCapacityPoint': 64.0,
#         'PermWiltingPoint': 41.0,
#     },
#     '8': {
#         'SaturationPoint': 71.0,
#         'FieldCapacityPoint': 66.0,
#         'PermWiltingPoint': 42.0,
#     },
#     '16': {
#         'SaturationPoint': 69.0,
#         'FieldCapacityPoint': 66.0,
#         'PermWiltingPoint': 42.0,
#     },
#     '24': {
#         'SaturationPoint': 74.0,
#         'FieldCapacityPoint': 73.0,
#         'PermWiltingPoint': 48.0,
#     },
#     '32': {
#         'SaturationPoint': 70.0,
#         'FieldCapacityPoint': 70.0,
#         'PermWiltingPoint': 45.0,
#     },
#     '40': {
#         'SaturationPoint': 64.0,
#         'FieldCapacityPoint': 64.0,
#         'PermWiltingPoint': 41.0,
#     },
# }
# multiplier = 1.3
# all_zones = ['4', '8', '16', '24', '32', '40']

# calcd_signal = {
#     'sm_units': sm_units,
#     'user_root_zones': user_root_zones,
#     'percent_of_FC': 0.92,
#     'percent_of_AWC': 0.83,
#     'GPP_required_to_reach_FC_high': 6.6,
#     'avg_draw_down_per_day': -2.0,
#     'est_days_to_next_irrigation': 5.7,
# }
