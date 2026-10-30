from django.shortcuts import render, redirect
from .forms import TripForm
from .api import get_coordinates, get_route, search_real_hotels, ROOM_CONFIGS
from .mcdm import rank_transport, rank_hotels
from .itinerary import create_weather_robust_plan
from .optimizer import (
    optimize_budget_portfolio,
    allocate_mystery_hotel,
    calculate_dynamic_room_price,
    calculate_tiered_cancellation_fee
)
from .qr import generate_qr_svg, generate_upi_qr_base64


def trip_view(request):
    """Trip planning view - handles location input, distance, MCDM, Itinerary & Budget Optimizer"""
    force_rainy = request.GET.get('rainy_mode') == '1'

    if request.method == 'POST' or ('rainy_mode' in request.GET and 'trip_destination' in request.session):
        if request.method == 'POST':
            form = TripForm(request.POST)
            if not form.is_valid():
                return render(request, 'trip_form.html', {'form': form})

            current_location = form.cleaned_data['current_location']
            destination = form.cleaned_data['destination']
            budget = float(form.cleaned_data.get('budget') or 5000.0)
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            people = form.cleaned_data.get('people') or 1
            most_important = form.cleaned_data.get('most_important') or 'cost'
            least_important = form.cleaned_data.get('least_important') or 'co2'
        else:
            current_location = request.session.get('trip_current_location', 'Mumbai')
            destination = request.session.get('trip_destination', 'Pune')
            budget = float(request.session.get('trip_budget', 5000.0))
            start_date = request.session.get('trip_start_date')
            end_date = request.session.get('trip_end_date')
            people = request.session.get('trip_people', 1)
            most_important = request.session.get('trip_most_important', 'cost')
            least_important = request.session.get('trip_least_important', 'co2')

        # Fetch coordinates
        start_coords = get_coordinates(current_location)
        dest_coords = get_coordinates(destination)

        if not start_coords or not dest_coords:
            error_msg = f"Failed to fetch coordinates for '{current_location}' or '{destination}'. Please check the location names."
            return render(request, 'error.html', {'message': error_msg})

        # Fetch route data
        start_lat, start_lon = start_coords
        dest_lat, dest_lon = dest_coords
        route_data = get_route(start_lat, start_lon, dest_lat, dest_lon)

        total_distance_km = 0.0
        try:
            routes = route_data.get('routes', [])
            if routes and len(routes) > 0:
                route = routes[0]
                legs = route.get('legs', [])
                if legs and len(legs) > 0 and 'summary' in legs[0]:
                    total_distance_km = legs[0]['summary']['lengthInMeters'] / 1000.0
                elif 'summary' in route and 'lengthInMeters' in route['summary']:
                    total_distance_km = route['summary']['lengthInMeters'] / 1000.0
        except Exception:
            total_distance_km = 0.0

        total_distance_float = float(total_distance_km)

        # 1. Multi-Criteria Transport Ranking (BWM + TOPSIS & MAUT with Genuine Live Pricing)
        mcdm_result = rank_transport(
            distance_km=total_distance_float,
            best_criterion=most_important,
            worst_criterion=least_important,
            origin=current_location,
            destination=destination,
            travel_date=str(start_date) if start_date else None
        )
        ranked_transports = mcdm_result['ranked_transports']
        recommended_transport = mcdm_result['recommended_transport']
        why_panel = mcdm_result['why_panel']

        # 2. Itinerary Builder (Orienteering Problem) & Weather-Robust Planning (Open-Meteo)
        itinerary_result = create_weather_robust_plan(
            destination_name=destination,
            lat=dest_lat,
            lon=dest_lon,
            num_days=3,
            budget=budget * 0.25,
            force_rainy=force_rainy
        )

        # 3. Budget Optimizer (Portfolio Decision Analysis / Knapsack Problem)
        portfolio_result = optimize_budget_portfolio(
            budget=budget,
            distance_km=total_distance_float,
            num_nights=2,
            num_people=people
        )

        # Store in session
        try:
            request.session['trip_current_location'] = current_location
            request.session['trip_destination'] = destination
            request.session['trip_dest_lat'] = dest_lat
            request.session['trip_dest_lon'] = dest_lon
            request.session['trip_budget'] = budget
            request.session['trip_distance'] = total_distance_float
            request.session['trip_most_important'] = most_important
            request.session['trip_least_important'] = least_important
            request.session['recommended_transport'] = recommended_transport['name']
            if start_date:
                request.session['trip_start_date'] = str(start_date)
            if end_date:
                request.session['trip_end_date'] = str(end_date)
            request.session['trip_people'] = people
        except Exception:
            pass

        return render(
            request,
            'success.html',
            {
                'current_location': current_location,
                'destination': destination,
                'budget': budget,
                'distance': total_distance_float,
                'ranked_transports': ranked_transports,
                'recommended_transport': recommended_transport,
                'why_panel': why_panel,
                'itinerary': itinerary_result,
                'portfolios': portfolio_result,
                'force_rainy': force_rainy,
                'most_important': most_important,
                'least_important': least_important,
                'people': people,
                'start_date': start_date,
                'end_date': end_date,
            }
        )
    else:
        # Pre-fill form from session
        initial_data = {}
        for k in ('trip_current_location', 'trip_destination', 'trip_budget', 'trip_start_date', 'trip_end_date', 'trip_people', 'trip_most_important', 'trip_least_important'):
            clean_k = k.replace('trip_', '')
            if k in request.session:
                initial_data[clean_k] = request.session[k]

        form = TripForm(initial=initial_data)

    return render(request, 'trip_form.html', {'form': form})

def final(request):
    """Hotel booking page with API real hotel search, multi-room size options, Dynamic Pricing & Cancellation Tiers"""
    destination = request.session.get('trip_destination', 'Jaipur, Rajasthan')
    dest_lat = request.session.get('trip_dest_lat')
    dest_lon = request.session.get('trip_dest_lon')
    checkin = request.GET.get('checkin') or request.session.get('trip_start_date', '')
    checkout = request.GET.get('checkout') or request.session.get('trip_end_date', '')
    guests = request.GET.get('guests') or request.session.get('trip_people', 1)

    # Room Size Configuration (1 Bed Room, 2 Bed Room, 3 Bed Room)
    room_type = request.GET.get('room_type') or request.session.get('trip_room_type', '1_bed')
    if room_type not in ROOM_CONFIGS:
        room_type = '1_bed'
    request.session['trip_room_type'] = room_type

    # 1. Search Real Hotels via TomTom API
    fetched_hotels = search_real_hotels(
        destination_name=destination,
        lat=dest_lat,
        lon=dest_lon,
        room_type=room_type
    )

    # 2. Dynamic Room Pricing (Perishable Inventory Model)
    demand_tracker = request.session.get('hotel_demand_tracker', {})
    dynamic_hotels = []
    for h in fetched_hotels:
        h_copy = dict(h)
        dp = calculate_dynamic_room_price(
            base_price=h['price'],
            checkin_date_str=checkin,
            demand_counter=demand_tracker.get(h['name'], 2)
        )
        h_copy['price'] = int(dp['final_price'])
        h_copy['dynamic_pricing'] = dp
        dynamic_hotels.append(h_copy)

    # 3. Opaque Mystery Hotel Deal (Balancing Policy)
    mystery_deal = allocate_mystery_hotel(tier='4_star', demand_tracker=demand_tracker)
    request.session['hotel_demand_tracker'] = demand_tracker
    request.session['active_mystery_deal'] = mystery_deal

    # 4. MAUT Hotel Ranking with Diminishing Returns
    trip_priority = request.session.get('trip_most_important', 'cost')
    hotel_priority = request.GET.get('hotel_priority')
    best_crit = hotel_priority if hotel_priority in ('price', 'rating', 'amenities') else ('rating' if trip_priority == 'comfort' else 'price')
    worst_crit = 'amenities' if best_crit != 'amenities' else 'rating'

    hotel_ranking = rank_hotels(dynamic_hotels, best_criterion=best_crit, worst_criterion=worst_crit)

    # 5. Tiered Cancellation Policy
    recommended_price = hotel_ranking['recommended_hotel']['price'] if hotel_ranking.get('recommended_hotel') else 2888
    cancellation_info = calculate_tiered_cancellation_fee(
        total_amount=recommended_price,
        checkin_date_str=checkin
    )

    context = {
        'destination': destination,
        'checkin': checkin,
        'checkout': checkout,
        'guests': guests,
        'room_type': room_type,
        'room_configs': ROOM_CONFIGS,
        'selected_room_config': ROOM_CONFIGS[room_type],
        'hotels': hotel_ranking['ranked_hotels'],
        'recommended_hotel': hotel_ranking['recommended_hotel'],
        'why_hotel_panel': hotel_ranking['why_panel'],
        'mystery_deal': mystery_deal,
        'cancellation_info': cancellation_info,
        'selected_priority': best_crit,
    }
    return render(request, 'booking.html', context)

def payment(request):
    """Booking details form page (forming)"""
    if request.method == 'POST':
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        passport = request.POST.get('passport', '').strip()
        address = request.POST.get('address', '').strip()

        request.session['booking_first_name'] = first_name
        request.session['booking_last_name'] = last_name
        request.session['booking_email'] = email
        request.session['booking_phone'] = phone
        request.session['booking_passport'] = passport
        request.session['booking_address'] = address

        # Calculate extras and total price
        base_price = float(request.session.get('hotel_price', 2888.0))
        extras = 0.0
        if request.POST.get('airportPickup'):
            extras += 2300.00
        if request.POST.get('activity'):
            extras += 2300.00
        if request.POST.get('massage'):
            extras += 2300.00
            
        total_price = base_price + extras
        request.session['booking_total_price'] = total_price
        return redirect('pay')

    # GET request - Capture hotel info (supports both regular hotel and Mystery Hotel Deal)
    is_mystery = request.GET.get('is_mystery') == '1'
    mystery_deal = request.session.get('active_mystery_deal', {})

    if is_mystery:
        if not mystery_deal:
            demand_tracker = request.session.get('hotel_demand_tracker', {})
            mystery_deal = allocate_mystery_hotel(tier='4_star', demand_tracker=demand_tracker)
            request.session['hotel_demand_tracker'] = demand_tracker
            request.session['active_mystery_deal'] = mystery_deal

        hotel_name = mystery_deal.get('opaque_title', '4★ Secret Express Mystery Deal')
        hotel_price = float(mystery_deal.get('discounted_price', 2240.0))
        request.session['is_mystery_booked'] = True
        request.session['mystery_revealed_name'] = mystery_deal.get('revealed_hotel', {}).get('name')
        request.session['mystery_savings'] = mystery_deal.get('savings', 960)
    else:
        hotel_name = request.GET.get('hotel_name') or request.session.get('hotel_name', 'FabExpress Ascot International')
        hotel_price_raw = request.GET.get('hotel_price') or request.session.get('hotel_price', 2888.0)
        try:
            hotel_price = float(hotel_price_raw)
        except (ValueError, TypeError):
            hotel_price = 2888.0
        request.session['is_mystery_booked'] = False

    room_type = request.GET.get('room_type')
    if room_type:
        request.session['room_type'] = room_type
    room_title = request.GET.get('room_title')
    if room_title:
        request.session['room_title'] = room_title

    request.session['hotel_name'] = hotel_name
    request.session['hotel_price'] = hotel_price
    request.session['booking_total_price'] = hotel_price

    destination = request.session.get('trip_destination', 'Kurla, Mumbai')
    checkin = request.session.get('trip_start_date', 'Upcoming Trip')
    guests = request.session.get('trip_people', 2)

    cancellation_info = calculate_tiered_cancellation_fee(hotel_price, checkin)

    context = {
        'hotel_name': hotel_name,
        'hotel_price': hotel_price,
        'destination': destination,
        'checkin': checkin,
        'guests': guests,
        'is_mystery': is_mystery,
        'cancellation_info': cancellation_info,
    }
    return render(request, 'form.html', context)

def pay(request):
    """Payment page with dynamic auto-filled UPI QR code and confirmation"""
    if request.method == 'POST':
        request.session['payment_status'] = 'COMPLETED'
        return redirect('booking_success')
        
    total_price = request.session.get('booking_total_price', request.session.get('hotel_price', 2888.0))
    checkin = request.session.get('trip_start_date', '')
    cancellation_info = calculate_tiered_cancellation_fee(total_price, checkin)

    # Generate dynamic UPI QR with auto-filled amount for Jiyanshu Jain
    upi_qr_base64, upi_url = generate_upi_qr_base64(total_price)

    context = {
        'total_price': float(total_price),
        'formatted_amount': f"{float(total_price):.2f}",
        'upi_qr_base64': upi_qr_base64,
        'upi_url': upi_url,
        'upi_id': 'jiyanshujain321@oksbi',
        'payee_name': 'Jiyanshu Jain',
        'cancellation_info': cancellation_info,
    }
    return render(request, 'payment.html', context)

def booking_success(request):
    """Final booking confirmation with Pure-Python QR Boarding Pass & Mystery Deal Reveal"""
    booking_email = request.session.get('booking_email') or 'guest@example.com'
    first_name = request.session.get('booking_first_name') or 'Guest'
    last_name = request.session.get('booking_last_name') or ''
    full_name = f"{first_name} {last_name}".strip()
    phone = request.session.get('booking_phone') or ''
    passengers = int(request.session.get('trip_people') or 1)

    # Generate safe reference ID
    email_clean = booking_email.split('@')[0] if '@' in booking_email else booking_email
    email_clean = ''.join(c for c in email_clean if c.isalnum()) or 'GUEST'
    booking_id = 'BK' + email_clean[:8].upper()

    total_price = request.session.get('booking_total_price', request.session.get('hotel_price', 2888.0))
    hotel_name = request.session.get('hotel_name', 'FabExpress Ascot International')
    destination = request.session.get('trip_destination', 'Kurla, Mumbai')
    checkin = request.session.get('trip_start_date', 'Confirmed Dates')

    # Handle Mystery Hotel Reveal
    is_mystery = request.session.get('is_mystery_booked', False)
    revealed_name = request.session.get('mystery_revealed_name')
    mystery_savings = request.session.get('mystery_savings', 0)
    property_name = revealed_name if (is_mystery and revealed_name) else hotel_name

    passenger_label = f"{passengers} Traveler{'s' if passengers > 1 else ''}"

    # Build comprehensive, scannable QR payload containing traveler details & passenger count
    phone_line = f"Phone: {phone}\n" if phone else ""
    qr_payload = (
        f"=== GOPLAN DIGITAL CHECK-IN PASS ===\n"
        f"Booking ID: #{booking_id}\n"
        f"Lead Traveler: {full_name}\n"
        f"Total Passengers: {passenger_label}\n"
        f"Email: {booking_email}\n"
        f"{phone_line}"
        f"Destination: {destination}\n"
        f"Stay: {property_name}\n"
        f"Check-In Date: {checkin}\n"
        f"Total Paid: Rs. {float(total_price):.2f}\n"
        f"Status: CONFIRMED & VERIFIED\n"
        f"==================================="
    )
    qr_svg = generate_qr_svg(qr_payload)

    # Tiered cancellation fee confirmation
    cancellation_info = calculate_tiered_cancellation_fee(total_price, checkin)

    context = {
        'booking_id': booking_id,
        'guest_name': full_name,
        'guest_email': booking_email,
        'phone': phone,
        'passengers': passengers,
        'total_price': float(total_price),
        'hotel_name': hotel_name,
        'destination': destination,
        'checkin': checkin,
        'is_mystery': is_mystery,
        'revealed_name': revealed_name,
        'mystery_savings': mystery_savings,
        'qr_svg': qr_svg,
        'cancellation_info': cancellation_info,
    }
    return render(request, 'booking_success.html', context)
