class IrrigationCalculations:

    @staticmethod
    def _calc_percent_fc_user_zones(user_root_zones,
                                    sm_units, vineyard_cfgs):
        percent_fc = []
        for zone in user_root_zones:
            percent_fc.append(sm_units[zone]['current']
                              / vineyard_cfgs[zone]['FieldCapacityPoint'])
        return percent_fc

    @staticmethod
    def calc_percent_fc_average_root_zone(user_root_zones,
                                            sm_units, vineyard_cfgs):
        percent_fc_zones = IrrigationCalculations._calc_percent_fc_user_zones(user_root_zones,
                                                      sm_units, vineyard_cfgs)
        fc_total = 0
        for zone in percent_fc_zones:
            fc_total = fc_total + zone
        return fc_total / len(user_root_zones)

    @staticmethod
    def _calc_percent_awc_user_zones(user_root_zones,
                                     sm_units, vineyard_cfgs):
        percent_awc = []
        for zone in user_root_zones:
            percent_awc.append(
                (sm_units[zone]['current']
                - vineyard_cfgs[zone]['PermWiltingPoint'])
                / (vineyard_cfgs[zone]['FieldCapacityPoint']
                - vineyard_cfgs[zone]['PermWiltingPoint']))
        return percent_awc

    @staticmethod
    def calc_percent_awc_average_root_zone(user_root_zones,
                                            sm_units, vineyard_cfgs):
        percent_awc_zones = IrrigationCalculations._calc_percent_awc_user_zones(user_root_zones,
                                                              sm_units,
                                                              vineyard_cfgs)
        awc_total = 0
        for zone in percent_awc_zones:
            awc_total = awc_total + zone
        return awc_total / len(user_root_zones)

    # Calculations for Gallons to Apply to Reach Target FC in Root Zone
    @staticmethod
    def _zones_above_user_input(user_root_zones, all_zones):
        zones_above = []
        for zone in all_zones:
            if zone not in user_root_zones and zone < min(user_root_zones):
                zones_above.append(zone)
        return zones_above

    @staticmethod
    def _calc_sm_deficit_sp_above_user_zones(user_root_zones,
                                             sm_units, all_zones,
                                             vineyard_cfgs):
        zones_above = IrrigationCalculations._zones_above_user_input(user_root_zones, all_zones)
        sm_units_sum = 0
        saturation_point_sum = 0
        for zone in zones_above:
            sm_units_sum = sm_units_sum + sm_units[zone]['current']
            saturation_point_sum = saturation_point_sum \
                                   + vineyard_cfgs[zone]['SaturationPoint']
        return sm_units_sum - saturation_point_sum

    @staticmethod
    def _calc_sm_deficit_fc_above_user_zones(user_root_zones,
                                             sm_units, all_zones,
                                             vineyard_cfgs):
        zones_above = IrrigationCalculations._zones_above_user_input(user_root_zones, all_zones)
        sm_units_sum = 0
        fc_point_sum = 0
        for zone in zones_above:
            sm_units_sum = sm_units_sum + sm_units[zone]['current']
            fc_point_sum = fc_point_sum \
                           + vineyard_cfgs[zone]['FieldCapacityPoint']
        return sm_units_sum - fc_point_sum

    @staticmethod
    def _calc_excess_sm_units_above_user_zones(user_root_zones,
                                               sm_units, all_zones,
                                               vineyard_cfgs):
        return IrrigationCalculations._calc_sm_deficit_sp_above_user_zones(user_root_zones,
                                                         sm_units,
                                                         all_zones,
                                                         vineyard_cfgs) \
               - IrrigationCalculations._calc_sm_deficit_fc_above_user_zones(user_root_zones,
                                                           sm_units,
                                                           all_zones,
                                                           vineyard_cfgs)

    @staticmethod
    def _calc_sm_deficit_user_zones(user_root_zones,
                                    sm_units, fc_high,
                                    vineyard_cfgs):
        sm_units_sum = 0
        fc_points_sum = 0
        for zone in user_root_zones:
            sm_units_sum += sm_units[zone]['current']
            fc_points_sum += vineyard_cfgs[zone]['FieldCapacityPoint']
        return sm_units_sum - (fc_points_sum * fc_high)

    @staticmethod
    def _calc_required_sm_increase_for_fc_high(user_root_zones,
                                               sm_units, fc_high,
                                               all_zones, vineyard_cfgs,
                                               multiplier):
        a = IrrigationCalculations._calc_sm_deficit_fc_above_user_zones(user_root_zones,
                                                      sm_units,
                                                      all_zones,
                                                      vineyard_cfgs)
        b = IrrigationCalculations._calc_sm_deficit_user_zones(user_root_zones, sm_units,
                                             fc_high, vineyard_cfgs)\
            * multiplier
        return a + b

    @staticmethod
    def _calc_absorption_rate(sm_units, last_irrigation_gpp):
        post_irrigation_sum = 0
        last_irrigated_sum = 0
        for zone in sm_units:
            post_irrigation_sum = post_irrigation_sum + sm_units[zone][
                '24hrs_post_irrigation']
            last_irrigated_sum = last_irrigated_sum + sm_units[zone][
                'last_irrigated']
        return (post_irrigation_sum - last_irrigated_sum) / last_irrigation_gpp

    @staticmethod
    def calc_gpp_required_to_reach_fc_goal(user_root_zones,
                                            sm_units, fc_high,
                                            last_irrigation_gpp, all_zones,
                                            vineyard_cfgs, multiplier):
        if IrrigationCalculations._calc_sm_deficit_user_zones(user_root_zones, sm_units,
                                            fc_high, vineyard_cfgs) < 0:
            return abs(
                IrrigationCalculations._calc_required_sm_increase_for_fc_high(user_root_zones,
                                                            sm_units,
                                                            fc_high,
                                                            all_zones,
                                                            vineyard_cfgs,
                                                            multiplier)
                / IrrigationCalculations._calc_absorption_rate(sm_units, last_irrigation_gpp))
        else:
            return 0

    # Calculations for Days Until Required Irrigation
    @staticmethod
    def _calc_total_draw_down_since_last_irrigation(sm_units):
        evaporation_estimates = {'4': 1, '8': 0.2}
        change_in_sm_units_exclude_evaporation = []
        for zone in sm_units:
            change_in_sm_units = sm_units[zone]['current'] - sm_units[zone][
                '24hrs_post_irrigation']
            evaporation = evaporation_estimates.get(zone, 0)
            change_in_sm_units_exclude_evaporation.append(
                change_in_sm_units - (change_in_sm_units * evaporation))
        return sum(change_in_sm_units_exclude_evaporation)

    @staticmethod
    def calc_average_drawdown_per_day(sm_units,
                                       last_irrigation_date, current_date):
        total_draw_down = IrrigationCalculations._calc_total_draw_down_since_last_irrigation(
            sm_units)
        return total_draw_down / ((current_date - last_irrigation_date).days)

    @staticmethod
    def _calc_sm_draw_down_to_target_irr_percent(user_root_zones,
                                                 sm_units, fc_low,
                                                 vineyard_cfgs):
        current_sm_sum = 0
        fc_point_sum = 0
        for zone in user_root_zones:
            current_sm_sum = current_sm_sum + sm_units[zone]['current']
            fc_point_sum = fc_point_sum \
                           + vineyard_cfgs[zone]['FieldCapacityPoint']
        fc_point_sum_fc_low = fc_point_sum * fc_low
        return fc_point_sum_fc_low - current_sm_sum

    @staticmethod
    def calc_est_days_until_irr(user_root_zones, sm_units,
                                 fc_low,last_irrigation_date,
                                 current_date, vineyard_cfgs):
        return IrrigationCalculations._calc_sm_draw_down_to_target_irr_percent(user_root_zones,
                                                             sm_units,
                                                             fc_low,
                                                             vineyard_cfgs) \
               / IrrigationCalculations.calc_average_drawdown_per_day(sm_units,
                                                     last_irrigation_date,
                                                     current_date)
