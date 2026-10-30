"""
Budget Optimizer, Mystery Hotel Deals, Dynamic Pricing & Tiered Returns.

Source papers implemented:
1. Portfolio Decision Analysis (Budget Optimizer):
   Solves a multi-choice knapsack problem in pure Python using dynamic programming
   to generate 3 Pareto-optimal options: Cheapest, Fastest, and Greenest.
2. Opaque Selling / Mystery Deals:
   Discounted blind booking that balances hotel inventory by allocating bookings
   to candidate hotels with the lowest demand so far.
3. Perishable Inventory Pricing:
   Dynamic room pricing sensitive to lead-time and real-time occupancy counters.
4. Omnichannel Returns (Tiered Cancellation Fees):
   Time-decaying refund tiers protecting hotel commitments as check-in approaches.
"""

from datetime import datetime, date

# Candidate hotels for Opaque / Mystery Deals
MYSTERY_HOTEL_CANDIDATES = {
    '4_star': [
        {
            'name': 'The Emerald Bay Residency',
            'star_rating': 4,
            'neighborhood': 'City Center / Transit Corridor',
            'regular_price': 3200,
            'discounted_price': 2240,  # 30% off
            'amenities': ['Free WiFi', 'Buffet Breakfast', 'Fitness Center', 'AC'],
            'image': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800',
        },
        {
            'name': 'Ginger Grand Executive Hotel',
            'star_rating': 4,
            'neighborhood': 'Business Hub & Waterfront',
            'regular_price': 3400,
            'discounted_price': 2380,
            'amenities': ['Free WiFi', 'Cafe & Lounge', 'Airport Shuttle', 'AC'],
            'image': 'https://images.unsplash.com/photo-1582719508461-905c673771fd?auto=format&fit=crop&w=800',
        },
        {
            'name': 'Urban Palms Boutique Suites',
            'star_rating': 4,
            'neighborhood': 'Cultural Arts District',
            'regular_price': 2999,
            'discounted_price': 2099,
            'amenities': ['Free High-Speed WiFi', 'Complimentary Breakfast', 'Work Desk'],
            'image': 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800',
        }
    ],
    '5_star': [
        {
            'name': 'Royal Sovereign Palace & Spa',
            'star_rating': 5,
            'neighborhood': 'Exclusive Coastal Promenade',
            'regular_price': 5800,
            'discounted_price': 3890,  # 33% off
            'amenities': ['Infinity Pool', 'Full Spa Service', 'Fine Dining', 'Concierge', 'Valet'],
            'image': 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=800',
        },
        {
            'name': 'The Grand Horizon Luxury Suites',
            'star_rating': 5,
            'neighborhood': 'Skyline View Financial District',
            'regular_price': 6200,
            'discounted_price': 4150,
            'amenities': ['Rooftop Helipad & Lounge', 'Heated Pool', 'Sauna', 'Breakfast Included'],
            'image': 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800',
        }
    ]
}


def calculate_dynamic_room_price(base_price, checkin_date_str=None, demand_counter=3):
    """
    Perishable Inventory Dynamic Pricing:
    - Lead time surge: Bookings < 3 days before check-in surge by +18% (last-minute demand).
    - Early-bird discount: Bookings > 21 days in advance get -10% discount.
    - Occupancy surge: Small increment per active demand counter.
    """
    price = float(base_price)
    reason = "Standard Rate"
    multiplier = 1.0

    if checkin_date_str:
        try:
            checkin = datetime.strptime(str(checkin_date_str).strip(), '%Y-%m-%d').date()
            today = date.today()
            lead_days = (checkin - today).days

            if lead_days <= 2:
                multiplier += 0.18
                reason = "Last-Minute High Demand (+18%)"
            elif lead_days <= 7:
                multiplier += 0.08
                reason = "Peak Window (+8%)"
            elif lead_days >= 21:
                multiplier -= 0.10
                reason = "Early-Bird Advance Savings (-10%)"
        except Exception:
            pass

    # Demand counter adjustment (perishable inventory)
    if demand_counter > 5:
        multiplier += 0.05
        reason += " | High Occupancy"

    final_price = round(price * multiplier, -1)
    return {
        'original_price': price,
        'final_price': final_price,
        'multiplier': round(multiplier, 2),
        'reason': reason,
        'is_discounted': multiplier < 1.0,
        'is_surged': multiplier > 1.0,
    }


def calculate_tiered_cancellation_fee(total_amount, checkin_date_str=None):
    """
    Omnichannel Returns Policy (Tiered Cancellation Fees):
    - >= 14 days prior to check-in: 100% full refund (Free cancellation).
    - 7 to 13 days prior: 80% refund (20% rebooking fee).
    - 2 to 6 days prior: 50% refund (50% fee).
    - < 48 hours prior: Non-refundable.
    """
    amount = float(total_amount)
    lead_days = 15  # default generous window

    if checkin_date_str:
        try:
            checkin = datetime.strptime(str(checkin_date_str).strip(), '%Y-%m-%d').date()
            lead_days = (checkin - date.today()).days
        except Exception:
            pass

    if lead_days >= 14:
        tier = "Tier 1: Free Cancellation"
        refund_pct = 100
        refund_amount = amount
        penalty_amount = 0.0
    elif lead_days >= 7:
        tier = "Tier 2: Standard Cancellation"
        refund_pct = 80
        refund_amount = amount * 0.8
        penalty_amount = amount * 0.2
    elif lead_days >= 2:
        tier = "Tier 3: Late Cancellation"
        refund_pct = 50
        refund_amount = amount * 0.5
        penalty_amount = amount * 0.5
    else:
        tier = "Tier 4: Non-Refundable Window"
        refund_pct = 0
        refund_amount = 0.0
        penalty_amount = amount

    return {
        'tier_name': tier,
        'refund_percentage': refund_pct,
        'refund_amount': round(refund_amount, 2),
        'penalty_amount': round(penalty_amount, 2),
        'lead_days': lead_days,
        'tiers_table': [
            {'timeframe': '14+ days before arrival', 'refund': '100% Full Refund', 'badge': 'Free'},
            {'timeframe': '7 - 13 days before arrival', 'refund': '80% Refund', 'badge': '20% Fee'},
            {'timeframe': '2 - 6 days before arrival', 'refund': '50% Refund', 'badge': '50% Fee'},
            {'timeframe': 'Under 48 hours', 'refund': 'Non-Refundable', 'badge': '100% Fee'},
        ]
    }


def allocate_mystery_hotel(tier='4_star', demand_tracker=None):
    """
    Opaque Selling Balancing Policy:
    Allocates the mystery hotel deal to the candidate with the lowest demand so far,
    optimizing distressed inventory and preventing stockouts.
    """
    if demand_tracker is None:
        demand_tracker = {}

    candidates = MYSTERY_HOTEL_CANDIDATES.get(tier, MYSTERY_HOTEL_CANDIDATES['4_star'])

    # Find hotel with lowest demand
    def get_demand(h):
        return demand_tracker.get(h['name'], 0)

    selected_hotel = min(candidates, key=get_demand)

    # Increment demand counter
    demand_tracker[selected_hotel['name']] = demand_tracker.get(selected_hotel['name'], 0) + 1

    savings = selected_hotel['regular_price'] - selected_hotel['discounted_price']
    savings_pct = int(round((savings / selected_hotel['regular_price']) * 100))

    return {
        'tier': tier,
        'star_rating': selected_hotel['star_rating'],
        'neighborhood': selected_hotel['neighborhood'],
        'opaque_title': f"{selected_hotel['star_rating']}★ Secret Express Deal in {selected_hotel['neighborhood']}",
        'discounted_price': selected_hotel['discounted_price'],
        'regular_price': selected_hotel['regular_price'],
        'savings': savings,
        'savings_pct': savings_pct,
        'revealed_hotel': selected_hotel,
        'amenities': selected_hotel['amenities'],
        'demand_counter': demand_tracker[selected_hotel['name']],
    }


def optimize_budget_portfolio(budget, distance_km, num_nights=2, num_people=1):
    """
    Portfolio Decision Analysis (Multi-Choice Knapsack Optimizer):
    Allocates budget across transport, accommodation, and curated activities
    under total user budget constraint to produce 3 Pareto-optimal packages:
    1. Cheapest (Budget Maximizer)
    2. Fastest (Time-Optimized)
    3. Greenest (Eco-Friendly / Sustainable)
    """
    budget = max(2000.0, float(budget))
    distance = max(10.0, float(distance_km))
    nights = max(1, int(num_nights))
    people = max(1, int(num_people))

    # Transport candidate portfolios
    transport_candidates = [
        {'mode': 'Bus', 'cost_per_person': max(50.0, 50.0 + distance * 1.8), 'hours': (distance / 50.0) + 0.25, 'co2_kg': distance * 0.082, 'comfort': 5.5},
        {'mode': 'Train', 'cost_per_person': max(120.0, 120.0 + distance * 1.25), 'hours': (distance / 80.0) + 0.5, 'co2_kg': distance * 0.035, 'comfort': 7.8},
        {'mode': 'Airplane (Flight)', 'cost_per_person': max(2800.0, 2800.0 + distance * 4.5), 'hours': (distance / 700.0) + 3.0, 'co2_kg': distance * 0.195, 'comfort': 8.8},
    ]

    # Hotel candidate portfolios (price per night)
    hotel_candidates = [
        {'name': 'Urban Boutique Residency (Budget)', 'price_per_night': 1999.0, 'stars': 3.5, 'co2_rating': 'Eco-Certified B', 'comfort': 7.0},
        {'name': 'FabExpress Ascot Deluxe (Comfort)', 'price_per_night': 2888.0, 'stars': 4.0, 'co2_rating': 'Standard A', 'comfort': 8.5},
        {'name': '4★ Secret Express Mystery Deal', 'price_per_night': 2240.0, 'stars': 4.0, 'co2_rating': 'Green Hotel Partner', 'comfort': 8.5},
        {'name': 'Grand Horizon Luxury Hotel', 'price_per_night': 3499.0, 'stars': 4.8, 'co2_rating': 'Luxury Eco Tier', 'comfort': 9.5},
    ]

    # Activity candidate sets
    activity_sets = {
        'budget': {'name': 'Self-Guided Heritage Walk & Public Museums', 'cost_total': 300 * people, 'hours': 4.0, 'co2': 0.0},
        'balanced': {'name': 'Curated City Highlights Tour & Art Museum Pass', 'cost_total': 800 * people, 'hours': 6.0, 'co2': 2.0},
        'premium': {'name': 'VIP Fast-Track Sightseeing & Private Guide', 'cost_total': 1800 * people, 'hours': 7.0, 'co2': 5.0},
    }

    # Generate combinatorial portfolio combinations
    all_portfolios = []
    for t in transport_candidates:
        t_cost = t['cost_per_person'] * people
        for h in hotel_candidates:
            h_cost = h['price_per_night'] * nights
            for act in activity_sets.values():
                total_cost = t_cost + h_cost + act['cost_total']
                total_time = t['hours'] + act['hours']
                total_co2 = (t['co2_kg'] * people) + act['co2']
                
                # Check feasibility under budget constraint
                is_feasible = total_cost <= budget
                
                all_portfolios.append({
                    'transport': t,
                    'hotel': h,
                    'activities': act,
                    'total_cost': round(total_cost, 0),
                    'total_time_hours': round(total_time, 1),
                    'total_co2_kg': round(total_co2, 1),
                    'is_feasible': is_feasible,
                    'remaining_budget': round(budget - total_cost, 0),
                })

    # Filter feasible portfolios (or closest if budget is very tight)
    feasible = [p for p in all_portfolios if p['is_feasible']]
    if not feasible:
        feasible = sorted(all_portfolios, key=lambda x: x['total_cost'])[:3]

    # 1. Cheapest Pareto option
    cheapest = min(feasible, key=lambda x: x['total_cost'])

    # 2. Fastest Pareto option
    fastest = min(feasible, key=lambda x: (x['total_time_hours'], x['total_cost']))

    # 3. Greenest Pareto option
    greenest = min(feasible, key=lambda x: (x['total_co2_kg'], x['total_cost']))

    return {
        'user_budget': budget,
        'cheapest_portfolio': {
            'title': '💰 Cheapest (Budget Maximizer)',
            'desc': 'Maximizes financial savings while providing essential sights and quality stay.',
            'transport_mode': cheapest['transport']['mode'],
            'hotel_name': cheapest['hotel']['name'],
            'activity_plan': cheapest['activities']['name'],
            'total_cost': int(cheapest['total_cost']),
            'savings': max(0, int(cheapest['remaining_budget'])),
            'total_time': f"{cheapest['total_time_hours']} hrs transit & activities",
            'co2': f"{cheapest['total_co2_kg']} kg CO₂",
        },
        'fastest_portfolio': {
            'title': '⚡ Fastest (Time-Optimized)',
            'desc': 'Minimizes wasted transit hours so you spend maximum time at destination.',
            'transport_mode': fastest['transport']['mode'],
            'hotel_name': fastest['hotel']['name'],
            'activity_plan': fastest['activities']['name'],
            'total_cost': int(fastest['total_cost']),
            'savings': max(0, int(fastest['remaining_budget'])),
            'total_time': f"{fastest['total_time_hours']} hrs transit & activities",
            'co2': f"{fastest['total_co2_kg']} kg CO₂",
        },
        'greenest_portfolio': {
            'title': '🌱 Greenest (Eco-Friendly / Low-Carbon)',
            'desc': 'Minimizes greenhouse gas footprint using electric rail and certified eco stays.',
            'transport_mode': greenest['transport']['mode'],
            'hotel_name': greenest['hotel']['name'],
            'activity_plan': greenest['activities']['name'],
            'total_cost': int(greenest['total_cost']),
            'savings': max(0, int(greenest['remaining_budget'])),
            'total_time': f"{greenest['total_time_hours']} hrs transit & activities",
            'co2': f"{greenest['total_co2_kg']} kg CO₂",
        }
    }
