"""
Multi-Criteria Decision Making (MCDM) module for GoPlan.

Source papers implemented:
1. Best-Worst Method (BWM) - Murad et al. / Rezaei (2015, 2016):
   Derives criteria weights using only 2n-3 comparisons from user's "most important"
   and "least important" criteria, avoiding full AHP pairwise comparisons and rank reversal.
2. Multi-Attribute Utility Theory (MAUT) - Gasparini et al.:
   Value functions for criteria, including diminishing returns for price.
3. Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS):
   Pure Python distance-to-ideal scoring.
4. Algorithmic Transparency - "Why this recommendation?" criterion score breakdown.
5. Live Genuine Pricing:
   Real-world IRCTC telescopic slabs, State Transport notifications, and live flight GDS feed.
"""

import math
from .live_prices import get_genuine_train_fare, get_genuine_bus_fare, fetch_live_flight_fare

TRANSPORT_SPECS = {
    'bus': {
        'name': 'Bus',
        'icon': '🚌',
        'speed_kmh': 50.0,
        'co2_per_km': 0.082,  # 82 g/pkm
        'comfort_score': 5.5,
        'overhead_hours': 0.25,
        'booking_url': 'https://www.makemytrip.com/bus-tickets/',
        'booking_label': 'Book Bus Tickets',
    },
    'train': {
        'name': 'Train',
        'icon': '🚂',
        'speed_kmh': 80.0,
        'co2_per_km': 0.035,  # 35 g/pkm
        'comfort_score': 7.8,
        'overhead_hours': 0.5,
        'booking_url': 'https://www.irctc.co.in/nget/train-search',
        'booking_label': 'Book Train on IRCTC',
    },
    'flight': {
        'name': 'Airplane (Flight)',
        'icon': '✈️',
        'speed_kmh': 700.0,
        'co2_per_km': 0.195,  # 195 g/pkm
        'comfort_score': 8.8,
        'overhead_hours': 3.0,
        'booking_url': 'https://www.goindigo.in/',
        'booking_label': 'Book Flight on IndiGo',
    }
}


def calculate_bwm_weights(criteria_keys, best_key, worst_key, custom_comparisons=None):
    """
    Best-Worst Method (BWM) - Rezaei / Murad et al.
    Derives optimal weights using user's choice of 'best' and 'worst' criteria.
    """
    n = len(criteria_keys)
    if n == 0:
        return {}
    if n == 1:
        return {criteria_keys[0]: 1.0}

    if best_key not in criteria_keys:
        best_key = criteria_keys[0]
    if worst_key not in criteria_keys:
        worst_key = criteria_keys[-1]

    best_idx = criteria_keys.index(best_key)
    worst_idx = criteria_keys.index(worst_key)

    if best_idx == worst_idx:
        equal_w = 1.0 / n
        return {k: round(equal_w, 4) for k in criteria_keys}

    a_b = {}
    a_w = {}

    for k in criteria_keys:
        if k == best_key:
            a_b[k] = 1.0
            a_w[k] = 8.0
        elif k == worst_key:
            a_b[k] = 8.0
            a_w[k] = 1.0
        else:
            a_b[k] = 3.0
            a_w[k] = 3.0

    if custom_comparisons:
        if 'a_b' in custom_comparisons:
            a_b.update(custom_comparisons['a_b'])
        if 'a_w' in custom_comparisons:
            a_w.update(custom_comparisons['a_w'])

    raw_b = [1.0 / a_b[k] for k in criteria_keys]
    raw_w = [float(a_w[k]) for k in criteria_keys]

    sum_b = sum(raw_b)
    sum_w = sum(raw_w)
    norm_b = [x / sum_b for x in raw_b]
    norm_w = [x / sum_w for x in raw_w]

    w = [(norm_b[i] + norm_w[i]) / 2.0 for i in range(n)]

    best_loss = 1e9
    best_w = list(w)

    for step_iter in range(120):
        wb = w[best_idx]
        ww = w[worst_idx]
        loss = 0.0
        for i, k in enumerate(criteria_keys):
            dev_b = abs(wb - a_b[k] * w[i])
            dev_w = abs(w[i] - a_w[k] * ww)
            loss = max(loss, dev_b, dev_w)

        if loss < best_loss:
            best_loss = loss
            best_w = list(w)

        for i in range(n):
            for j in range(i + 1, n):
                for delta in (-0.015, -0.005, 0.005, 0.015):
                    if w[i] + delta > 0.02 and w[j] - delta > 0.02:
                        w[i] += delta
                        w[j] -= delta
                        wb_t = w[best_idx]
                        ww_t = w[worst_idx]
                        cur_loss = max(
                            max(abs(wb_t - a_b[criteria_keys[m]] * w[m]) for m in range(n)),
                            max(abs(w[m] - a_w[criteria_keys[m]] * ww_t) for m in range(n))
                        )
                        if cur_loss < best_loss:
                            best_loss = cur_loss
                            best_w = list(w)
                        else:
                            w[i] -= delta
                            w[j] += delta

    total_w = sum(best_w)
    normalized = {criteria_keys[i]: round(best_w[i] / total_w, 4) for i in range(n)}
    return normalized


def estimate_transport_attributes(distance_km, origin='Mumbai', destination='Pune', travel_date=None):
    """
    Computes real, genuine ticket pricing and transit metrics:
    - Train: Exact published Indian Railways passenger tariff slab.
    - Bus: Official state transport notified slab rate.
    - Flight: Live flight market feed / Amadeus GDS with Google Flights live link.
    """
    distance = max(1.0, float(distance_km))
    estimates = {}

    # Fetch genuine fares
    train_fare_data = get_genuine_train_fare(distance)
    bus_fare_data = get_genuine_bus_fare(distance)
    flight_fare_data = fetch_live_flight_fare(origin, destination, travel_date, distance)

    for mode_key, specs in TRANSPORT_SPECS.items():
        # Travel time in hours
        travel_hours = (distance / specs['speed_kmh']) + specs['overhead_hours']
        
        hours_int = int(travel_hours)
        mins_int = int(round((travel_hours - hours_int) * 60))
        if mins_int == 60:
            hours_int += 1
            mins_int = 0
        if hours_int > 0:
            time_display = f"{hours_int}h {mins_int}m"
        else:
            time_display = f"{mins_int} mins"

        # CO2 emissions in kg
        estimated_co2 = round(distance * specs['co2_per_km'], 1)
        co2_display = f"{estimated_co2} kg CO₂"

        # Comfort score (1-10)
        comfort = specs['comfort_score']
        if mode_key == 'bus' and travel_hours > 12:
            comfort = max(2.5, comfort - (travel_hours - 12) * 0.25)

        # Real Ticket Fares
        booking_url = specs['booking_url']
        if mode_key == 'train':
            fare_cost = float(train_fare_data['fare'])
            fare_display = f"Rs. {int(fare_cost)}"
            fare_source = train_fare_data['source']
            fare_subtitle = train_fare_data['class_name']
        elif mode_key == 'bus':
            fare_cost = float(bus_fare_data['fare'])
            fare_display = f"Rs. {int(fare_cost)}"
            fare_source = bus_fare_data['source']
            fare_subtitle = bus_fare_data['class_name']
        else:  # flight
            fare_cost = float(flight_fare_data['fare'])
            fare_display = f"Rs. {int(fare_cost):,}"
            fare_source = flight_fare_data['source']
            fare_subtitle = "Economy Non-Stop"
            booking_url = flight_fare_data['google_flights_url']

        estimates[mode_key] = {
            'key': mode_key,
            'name': specs['name'],
            'icon': specs['icon'],
            'booking_url': booking_url,
            'booking_label': specs['booking_label'],
            'raw': {
                'cost': fare_cost,
                'time': travel_hours,
                'co2': estimated_co2,
                'comfort': comfort,
            },
            'display': {
                'cost': fare_display,
                'fare_source': fare_source,
                'fare_subtitle': fare_subtitle,
                'time': time_display,
                'co2': co2_display,
                'comfort': f"{comfort:.1f} / 10",
            }
        }

    return estimates


def topsis_rank(alternatives, weights, criteria_types):
    """
    TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution) in pure Python.
    """
    keys = [a['key'] for a in alternatives]
    crit_keys = list(weights.keys())

    norm_divisors = {}
    for c in crit_keys:
        sq_sum = sum(a['raw'][c] ** 2 for a in alternatives)
        norm_divisors[c] = math.sqrt(sq_sum) if sq_sum > 0 else 1.0

    v = {a['key']: {} for a in alternatives}
    for a in alternatives:
        k = a['key']
        for c in crit_keys:
            r_ij = a['raw'][c] / norm_divisors[c]
            v[k][c] = weights[c] * r_ij

    v_best = {}
    v_worst = {}
    for c in crit_keys:
        values = [v[k][c] for k in keys]
        if criteria_types[c] == 'max':
            v_best[c] = max(values)
            v_worst[c] = min(values)
        else:
            v_best[c] = min(values)
            v_worst[c] = max(values)

    s_best = {}
    s_worst = {}
    closeness = {}

    for k in keys:
        d_best_sq = sum((v[k][c] - v_best[c]) ** 2 for c in crit_keys)
        d_worst_sq = sum((v[k][c] - v_worst[c]) ** 2 for c in crit_keys)
        s_best[k] = math.sqrt(d_best_sq)
        s_worst[k] = math.sqrt(d_worst_sq)

        denominator = s_best[k] + s_worst[k]
        if denominator > 0:
            closeness[k] = round(s_worst[k] / denominator, 4)
        else:
            closeness[k] = 0.5

    return closeness


def calculate_maut_utilities(alternatives, weights, criteria_types):
    """
    MAUT (Multi-Attribute Utility Theory - Gasparini et al.)
    Provides normalized marginal utilities u_j in [0, 1] and weighted contributions.
    """
    crit_keys = list(weights.keys())
    
    ranges = {}
    for c in crit_keys:
        vals = [a['raw'][c] for a in alternatives]
        min_v = min(vals)
        max_v = max(vals)
        ranges[c] = (min_v, max_v)

    breakdown = {}
    for a in alternatives:
        k = a['key']
        breakdown[k] = {
            'marginal': {},
            'weighted': {},
            'total_utility': 0.0,
        }
        total_u = 0.0
        for c in crit_keys:
            val = a['raw'][c]
            min_v, max_v = ranges[c]
            diff = max_v - min_v

            if diff == 0:
                u = 1.0
            elif criteria_types[c] == 'min':
                u = (max_v - val) / diff
            else:
                u = (val - min_v) / diff

            if c == 'cost' and u > 0:
                u = math.sqrt(u)

            u = max(0.0, min(1.0, u))
            weighted_u = round(weights[c] * u, 4)
            total_u += weighted_u

            breakdown[k]['marginal'][c] = round(u * 100, 1)
            breakdown[k]['weighted'][c] = weighted_u

        breakdown[k]['total_utility'] = round(total_u, 4)

    return breakdown


def rank_transport(distance_km, best_criterion='cost', worst_criterion='co2', origin='Mumbai', destination='Pune', travel_date=None):
    """
    Multi-criteria transport ranking using BWM + TOPSIS + MAUT transparency with real-market ticket pricing.
    """
    criteria_keys = ['cost', 'time', 'co2', 'comfort']
    criteria_types = {
        'cost': 'min',
        'time': 'min',
        'co2': 'min',
        'comfort': 'max',
    }
    criteria_labels = {
        'cost': 'Cost / Budget',
        'time': 'Travel Time',
        'co2': 'Carbon Footprint (CO₂)',
        'comfort': 'Comfort & Convenience',
    }

    # 1. BWM weights
    weights = calculate_bwm_weights(criteria_keys, best_criterion, worst_criterion)

    # 2. Genuine ticket pricing and transit metrics
    estimates = estimate_transport_attributes(distance_km, origin, destination, travel_date)
    alt_list = list(estimates.values())

    # 3. TOPSIS & MAUT scoring
    topsis_scores = topsis_rank(alt_list, weights, criteria_types)
    maut_breakdown = calculate_maut_utilities(alt_list, weights, criteria_types)

    # 4. Rank alternatives
    ranked = []
    for item in alt_list:
        k = item['key']
        composite_score = round(0.5 * topsis_scores[k] + 0.5 * maut_breakdown[k]['total_utility'], 4)
        
        item_scores = {
            'cost_utility': maut_breakdown[k]['marginal']['cost'],
            'time_utility': maut_breakdown[k]['marginal']['time'],
            'co2_utility': maut_breakdown[k]['marginal']['co2'],
            'comfort_utility': maut_breakdown[k]['marginal']['comfort'],
            'weighted_contributions': maut_breakdown[k]['weighted'],
            'topsis_score': topsis_scores[k],
            'composite_score': composite_score,
            'composite_pct': round(composite_score * 100, 1),
        }

        ranked.append({
            'key': k,
            'name': item['name'],
            'icon': item['icon'],
            'display': item['display'],
            'raw': item['raw'],
            'scores': item_scores,
            'booking_url': item['booking_url'],
            'booking_label': item['booking_label'],
        })

    ranked.sort(key=lambda x: x['scores']['composite_score'], reverse=True)

    for idx, item in enumerate(ranked):
        item['rank'] = idx + 1
        if idx == 0:
            item['badge'] = '🏆 #1 Top Recommended'
        elif idx == 1:
            item['badge'] = '🥈 #2 Strong Alternative'
        else:
            item['badge'] = '🥉 #3 Alternative Option'

    winner = ranked[0]
    explanation = (
        f"{winner['name']} ranks #1 with a {winner['scores']['composite_pct']}% match score. "
        f"Based on your high priority for '{criteria_labels.get(best_criterion)}' ({int(weights[best_criterion]*100)}% weight), "
        f"{winner['name']} provides optimal value at {winner['display']['cost']} "
        f"with a {winner['display']['time']} journey duration."
    )

    why_panel = {
        'winner_name': winner['name'],
        'winner_icon': winner['icon'],
        'explanation': explanation,
        'best_criterion_label': criteria_labels.get(best_criterion, best_criterion),
        'worst_criterion_label': criteria_labels.get(worst_criterion, worst_criterion),
        'weights_display': {
            criteria_labels[k]: round(weights[k] * 100, 1) for k in criteria_keys
        },
        'criteria_weights': weights,
    }

    return {
        'ranked_transports': ranked,
        'recommended_transport': winner,
        'why_panel': why_panel,
        'distance_km': distance_km,
    }


def maut_hotel_value_function(price, rating, amenities_count, min_p, max_p):
    """
    MAUT-style value functions for hotels (Gasparini et al.):
    - Price: lower is better, with diminishing returns.
    - Rating: higher is better.
    - Amenities: higher is better.
    """
    if max_p > min_p:
        raw_price_norm = max(0.0, min(1.0, (max_p - price) / (max_p - min_p)))
        u_price = math.sqrt(raw_price_norm)
    else:
        u_price = 1.0

    u_rating = max(0.0, min(1.0, (rating - 3.5) / 1.5)) ** 1.2
    u_amenities = max(0.0, min(1.0, amenities_count / 5.0))

    return {
        'price_utility': round(u_price * 100, 1),
        'rating_utility': round(u_rating * 100, 1),
        'amenities_utility': round(u_amenities * 100, 1),
        'raw_utilities': {
            'price': u_price,
            'rating': u_rating,
            'amenities': u_amenities,
        }
    }


def rank_hotels(hotels_list, best_criterion='price', worst_criterion='amenities'):
    """
    Ranks hotels using MAUT value functions with diminishing returns on price.
    """
    criteria_keys = ['price', 'rating', 'amenities']
    criteria_labels = {
        'price': 'Nightly Price & Value',
        'rating': 'Guest Review Rating',
        'amenities': 'Included Amenities',
    }

    weights = calculate_bwm_weights(criteria_keys, best_criterion, worst_criterion)

    if not hotels_list:
        return {'ranked_hotels': [], 'why_panel': None}

    prices = [h['price'] for h in hotels_list]
    min_p = min(prices)
    max_p = max(prices)

    ranked = []
    for h in hotels_list:
        amenities_count = len(h.get('amenities', [])) or 3
        rating = float(h.get('rating', 4.5))
        price = float(h['price'])

        utilities = maut_hotel_value_function(price, rating, amenities_count, min_p, max_p)
        u_dict = utilities['raw_utilities']

        overall_utility = (
            weights['price'] * u_dict['price'] +
            weights['rating'] * u_dict['rating'] +
            weights['amenities'] * u_dict['amenities']
        )
        overall_score = round(overall_utility * 100, 1)

        hotel_data = dict(h)
        hotel_data['overall_score'] = overall_score
        hotel_data['utilities'] = utilities
        ranked.append(hotel_data)

    ranked.sort(key=lambda x: x['overall_score'], reverse=True)

    for idx, h in enumerate(ranked):
        h['rank'] = idx + 1
        if idx == 0:
            h['badge'] = '🌟 Best Match'
        elif idx == 1:
            h['badge'] = '✨ Great Choice'
        else:
            h['badge'] = '👍 Good Value'

    winner = ranked[0]
    why_explanation = (
        f"'{winner['name']}' achieved the top rank ({winner['overall_score']}%) based on your preferences. "
        f"It offers {winner['utilities']['price_utility']}% price-value utility (diminishing return model) "
        f"and {winner['rating']}★ guest satisfaction."
    )

    why_panel = {
        'winner_name': winner['name'],
        'explanation': why_explanation,
        'weights_display': {
            criteria_labels[k]: round(weights[k] * 100, 1) for k in criteria_keys
        }
    }

    return {
        'ranked_hotels': ranked,
        'recommended_hotel': winner,
        'why_panel': why_panel,
    }
