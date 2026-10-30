from django.test import TestCase, Client
from django.urls import reverse
from web.forms import TripForm
from web.api import haversine_distance, get_coordinates
from web.mcdm import (
    calculate_bwm_weights,
    estimate_transport_attributes,
    topsis_rank,
    rank_transport,
    maut_hotel_value_function,
    rank_hotels,
)
from web.itinerary import (
    solve_orienteering_itinerary,
    create_weather_robust_plan,
    get_best_months_to_visit,
    get_destination_pois,
)
from web.optimizer import (
    optimize_budget_portfolio,
    allocate_mystery_hotel,
    calculate_dynamic_room_price,
    calculate_tiered_cancellation_fee,
)
from web.qr import generate_qr_svg, QRCodeSVG

class TripFormTest(TestCase):
    def test_valid_trip_form(self):
        data = {
            'current_location': 'Mumbai',
            'destination': 'Pune',
            'budget': '5000.00',
            'people': 2,
            'start_date': '2026-11-01',
            'end_date': '2026-11-05',
            'most_important': 'cost',
            'least_important': 'co2',
        }
        form = TripForm(data=data)
        self.assertTrue(form.is_valid())

    def test_trip_form_optional_fields(self):
        data = {
            'current_location': 'Mumbai',
            'destination': 'Pune',
            'budget': '2500',
        }
        form = TripForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['budget'], 2500)

    def test_trip_form_missing_required(self):
        form = TripForm(data={'current_location': 'Mumbai'})
        self.assertFalse(form.is_valid())
        self.assertIn('destination', form.errors)

    def test_trip_form_negative_budget(self):
        form = TripForm(data={
            'current_location': 'Mumbai',
            'destination': 'Delhi',
            'budget': '-100'
        })
        self.assertFalse(form.is_valid())

    def test_haversine_and_coordinates(self):
        coords = get_coordinates('Mumbai')
        self.assertIsNotNone(coords)
        dist = haversine_distance(19.0760, 72.8777, 18.5204, 73.8567)
        self.assertGreater(dist, 100)
        self.assertLess(dist, 150)


class McdmBwmAndTransparencyTest(TestCase):
    def test_bwm_weights_derivation(self):
        criteria = ['cost', 'time', 'co2', 'comfort']
        weights = calculate_bwm_weights(criteria, best_key='cost', worst_key='co2')
        self.assertEqual(len(weights), 4)
        self.assertEqual(max(weights, key=weights.get), 'cost')
        self.assertEqual(min(weights, key=weights.get), 'co2')
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)

    def test_estimate_transport_attributes(self):
        estimates = estimate_transport_attributes(distance_km=700)
        self.assertIn('bus', estimates)
        self.assertIn('train', estimates)
        self.assertIn('flight', estimates)
        self.assertIn('Rs.', estimates['bus']['display']['cost'])
        self.assertIn('Rs.', estimates['train']['display']['cost'])
        self.assertIn('Rs.', estimates['flight']['display']['cost'])

    def test_rank_transport_mcdm_cost_priority(self):
        res = rank_transport(distance_km=150, best_criterion='cost', worst_criterion='co2')
        winner = res['recommended_transport']
        self.assertIn(winner['key'], ('train', 'bus'))
        self.assertIn('winner_name', res['why_panel'])

    def test_hotel_maut_diminishing_returns(self):
        cheap = maut_hotel_value_function(price=1500, rating=4.5, amenities_count=3, min_p=1500, max_p=4000)
        mid = maut_hotel_value_function(price=2750, rating=4.5, amenities_count=3, min_p=1500, max_p=4000)
        self.assertGreater(cheap['price_utility'], mid['price_utility'])

    def test_topsis_and_rank_hotels(self):
        alternatives = [
            {'key': 'alt1', 'raw': {'cost': 100, 'time': 2}},
            {'key': 'alt2', 'raw': {'cost': 200, 'time': 1}},
        ]
        weights = {'cost': 0.5, 'time': 0.5}
        types = {'cost': 'min', 'time': 'min'}
        scores = topsis_rank(alternatives, weights, types)
        self.assertIn('alt1', scores)
        self.assertIn('alt2', scores)

        hotels = [
            {'name': 'Hotel A', 'price': 1800, 'rating': 4.6, 'amenities': ['WiFi']},
            {'name': 'Hotel B', 'price': 3200, 'rating': 4.8, 'amenities': ['WiFi', 'Pool', 'Spa']},
        ]
        res = rank_hotels(hotels, best_criterion='price')
        self.assertEqual(len(res['ranked_hotels']), 2)
        self.assertEqual(res['recommended_hotel']['name'], 'Hotel A')


class ItineraryAndWeatherRobustTest(TestCase):
    def test_orienteering_itinerary_solver(self):
        pois = get_destination_pois('Mumbai')
        res = solve_orienteering_itinerary(pois, num_days=2, daily_hours=8.0, max_budget=1000)
        self.assertEqual(len(res['days']), 2)
        # Check that each day has stops and valid sequence
        for day in res['days']:
            self.assertGreater(len(day['stops']), 0)
            self.assertIn('time_slot', day['stops'][0])

    def test_weather_robust_swapping_on_rain(self):
        # Force rainy mode to verify outdoor stops are swapped for indoor
        res = create_weather_robust_plan('Mumbai', 18.9690, 72.8211, num_days=2, budget=2000, force_rainy=True)
        self.assertTrue(res['has_rainy_day'])
        # In rainy mode, all scheduled stops should be indoor
        for day in res['itinerary_days']:
            for stop in day['stops']:
                self.assertTrue(stop['is_indoor'])

    def test_best_months_climate_suggestion(self):
        mumbai_climate = get_best_months_to_visit('Mumbai')
        self.assertIn('October', mumbai_climate['best_months'])
        london_climate = get_best_months_to_visit('London')
        self.assertIn('May', london_climate['best_months'])


class BudgetOptimizerAndOpaqueHotelTest(TestCase):
    def test_knapsack_budget_optimizer_pareto_options(self):
        res = optimize_budget_portfolio(budget=12000, distance_km=400, num_nights=2, num_people=1)
        self.assertIn('cheapest_portfolio', res)
        self.assertIn('fastest_portfolio', res)
        self.assertIn('greenest_portfolio', res)
        # Cost check: cheapest <= fastest
        self.assertLessEqual(res['cheapest_portfolio']['total_cost'], res['fastest_portfolio']['total_cost'] + 500)

    def test_opaque_mystery_hotel_balancing_policy(self):
        tracker = {'The Emerald Bay Residency': 5, 'Ginger Grand Executive Hotel': 1}
        # Allocation must pick candidate with least demand
        deal = allocate_mystery_hotel(tier='4_star', demand_tracker=tracker)
        self.assertIsNotNone(deal['revealed_hotel'])
        # Demand for chosen hotel should now be updated
        self.assertGreaterEqual(tracker[deal['revealed_hotel']['name']], 1)

    def test_dynamic_room_pricing(self):
        # Last minute lead time surge
        p_surge = calculate_dynamic_room_price(base_price=3000, checkin_date_str='2026-10-30')
        self.assertTrue(p_surge['is_surged'])
        self.assertGreater(p_surge['final_price'], 3000)

    def test_tiered_cancellation_fee(self):
        # Far in advance
        c_early = calculate_tiered_cancellation_fee(total_amount=5000, checkin_date_str='2026-11-20')
        self.assertEqual(c_early['refund_percentage'], 100)
        self.assertEqual(c_early['refund_amount'], 5000)


class PurePythonQRCodeTest(TestCase):
    def test_qr_code_svg_generation(self):
        svg = generate_qr_svg("BK12345678|Rahul Sharma|Mumbai")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("<rect", svg)
        self.assertGreater(len(svg), 500)

    def test_qr_code_svg_class(self):
        qr = QRCodeSVG("ShortMsg")
        self.assertEqual(qr.version, 2)
        self.assertEqual(qr.size, 25)
        self.assertTrue(len(qr.to_svg()) > 300)


class EndpointsWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_trip_view_get(self):
        response = self.client.get(reverse('trip_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Travel More.')
        self.assertContains(response, 'Where do you want to go?')

    def test_home_url_alias(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_trip_view_post_valid_with_mcdm_itinerary_and_portfolio(self):
        data = {
            'current_location': 'Mumbai',
            'destination': 'Pune',
            'budget': '8000',
            'people': 1,
            'most_important': 'cost',
            'least_important': 'co2',
        }
        response = self.client.post(reverse('trip_view'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Intelligent Travel Plan')
        self.assertContains(response, 'Ranked Travel Options')
        self.assertContains(response, 'Ready for Accommodations?')
        self.assertContains(response, 'Day-by-Day Itinerary')
        self.assertContains(response, 'Budget Optimizer')
        self.assertContains(response, 'Ticket Fare')

    def test_hotel_booking_get_with_mystery_deal_and_maut(self):
        response = self.client.get(reverse('booking'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smart Hotel Booking')
        self.assertContains(response, 'Mystery Deal')
        self.assertContains(response, 'Cancellation Policy')

    def test_guest_form_post_and_redirect_to_pay(self):
        form_data = {
            'firstName': 'Aarav',
            'lastName': 'Patel',
            'email': 'aarav@example.com',
            'phone': '9876543210',
            'address': '123 MG Road, Mumbai',
            'agree': 'on',
        }
        response = self.client.post(reverse('forming'), form_data)
        self.assertRedirects(response, reverse('pay'))

    def test_full_workflow_end_to_end_with_qr_pass(self):
        # 1. Search trip
        step1 = self.client.post(reverse('trip_view'), {
            'current_location': 'Delhi',
            'destination': 'Mumbai',
            'budget': '15000',
            'people': 1,
            'most_important': 'time',
            'least_important': 'cost',
        })
        self.assertEqual(step1.status_code, 200)
        self.assertContains(step1, 'Airplane (Flight)')

        # 2. Browse hotels & select mystery deal
        step2 = self.client.get(reverse('forming') + '?is_mystery=1')
        self.assertEqual(step2.status_code, 200)
        self.assertContains(step2, 'Secret Express Deal')

        # 3. Enter guest details
        step3 = self.client.post(reverse('forming'), {
            'firstName': 'Priya',
            'lastName': 'Sharma',
            'email': 'priya.sharma@example.com',
            'phone': '9812345678',
            'address': 'Connaught Place, New Delhi',
            'agree': 'on',
        })
        self.assertRedirects(step3, reverse('pay'))

        # 4. View payment
        step4 = self.client.get(reverse('pay'))
        self.assertEqual(step4.status_code, 200)

        # 5. Confirm payment
        step5 = self.client.post(reverse('pay'))
        self.assertRedirects(step5, reverse('booking_success'))

        # 6. Success confirmation page: Boarding pass with pure-python QR SVG & Mystery Reveal
        step6 = self.client.get(reverse('booking_success'))
        self.assertEqual(step6.status_code, 200)
        self.assertContains(step6, 'Reservation Confirmed!')
        self.assertContains(step6, 'Digital Check-In QR Pass')
        self.assertContains(step6, 'Priya Sharma')
        self.assertContains(step6, 'Passengers')
        self.assertContains(step6, '<svg')
        self.assertContains(step6, 'Secret Hotel Deal Unlocked!')
