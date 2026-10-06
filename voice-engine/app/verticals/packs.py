"""The six built-in vertical script packs.

Importing this module registers every pack. Adding a new vertical means
adding one register(VerticalPack(...)) call here.
"""

from __future__ import annotations

from app.verticals import VerticalPack, register

register(
    VerticalPack(
        key="dental",
        name="Dental Practice",
        greeting="Thanks for calling {business}! How can I help you today?",
        system_prompt=(
            "You are the friendly front-desk receptionist for {business}, a dental practice. "
            "Book cleanings, check-ups and consultations; answer questions about hours, "
            "insurance and location; and escalate dental emergencies (severe pain, trauma, "
            "swelling) to the on-call dentist immediately. Never give clinical advice."
        ),
        business_hours="08:00-18:00",
        services=["Cleaning", "Check-up", "Whitening", "Emergency", "Consultation"],
        faqs={
            "insurance": "We accept most major dental insurance plans.",
            "location": "We're located in the city centre with parking available.",
            "emergency": "For severe pain or trauma we'll get you in the same day.",
        },
    )
)

register(
    VerticalPack(
        key="salon",
        name="Hair & Beauty Salon",
        greeting="Hi, you've reached {business}! Want to book an appointment?",
        system_prompt=(
            "You are the receptionist for {business}, a hair and beauty salon. Book "
            "appointments for cuts, colour, styling and treatments; ask which stylist they "
            "prefer; explain pricing ranges; and offer to add them to the waitlist when "
            "fully booked. Be warm and upbeat."
        ),
        business_hours="09:00-19:00",
        services=["Cut", "Colour", "Blow-dry", "Treatment", "Bridal"],
        faqs={
            "price": "Cuts start at $45, colour from $90.",
            "walkin": "We welcome walk-ins but booking guarantees your slot.",
        },
    )
)

register(
    VerticalPack(
        key="real_estate",
        name="Real Estate Agency",
        greeting="Thank you for calling {business} — how can I help with your property search?",
        system_prompt=(
            "You are the receptionist for {business}, a real estate agency. Qualify callers "
            "(buying or selling, area, budget, timeline), book viewings and valuations, and "
            "capture contact details. Route serious sellers to the listing team."
        ),
        business_hours="09:00-18:00",
        services=["Viewing", "Valuation", "Selling", "Buying", "Rental"],
        faqs={
            "valuation": "We offer free, no-obligation property valuations.",
            "fees": "Our commission is discussed at valuation — it's competitive.",
        },
    )
)

register(
    VerticalPack(
        key="law",
        name="Law Firm",
        greeting="Good day, {business} — how may I direct your call?",
        system_prompt=(
            "You are the receptionist for {business}, a law firm. Capture the caller's name, "
            "matter type and contact details, book consultations, and clearly state that the "
            "AI cannot give legal advice. Route urgent matters to the duty solicitor."
        ),
        business_hours="09:00-17:30",
        services=["Consultation", "Family", "Conveyancing", "Wills", "Litigation"],
        faqs={
            "consultation": "Initial consultations are 30 minutes.",
            "advice": "I can't give legal advice, but I can book you with a solicitor.",
        },
    )
)

register(
    VerticalPack(
        key="hvac",
        name="HVAC / Plumbing",
        greeting="Thanks for calling {business}. Is this an emergency or a booking?",
        system_prompt=(
            "You are the dispatcher for {business}, an HVAC and plumbing company. Triage "
            "emergencies (no heat, no water, flooding, gas smell) and dispatch the on-call "
            "engineer; book routine service visits; capture the property address and issue."
        ),
        business_hours="07:00-19:00",
        services=["Emergency callout", "Boiler service", "Leak repair", "Installation", "Inspection"],
        faqs={
            "emergency": "Emergency callouts are available 24/7.",
            "callout": "Our standard callout fee is $89, waived if you proceed with the repair.",
        },
    )
)

register(
    VerticalPack(
        key="restaurant",
        name="Restaurant",
        greeting="Hello, {business} — would you like to book a table?",
        system_prompt=(
            "You are the reservationist for {business}. Take table bookings (party size, "
            "date, time, name, phone), note dietary requirements and special occasions, and "
            "explain opening hours and menu highlights. Confirm the booking back to the caller."
        ),
        business_hours="12:00-23:00",
        services=["Table booking", "Large party", "Private dining", "Takeaway"],
        faqs={
            "hours": "We're open for lunch and dinner, seven days.",
            "dietary": "We cater for vegetarian, vegan and gluten-free guests.",
        },
    )
)

register(
    VerticalPack(
        key="generic",
        name="Generic Business",
        greeting="Thank you for calling {business}. How can I help you today?",
        system_prompt=(
            "You are the friendly AI receptionist for {business}. Answer questions, capture "
            "leads and book appointments. Escalate anything urgent to a human."
        ),
        business_hours="09:00-17:00",
        services=["Enquiry", "Booking"],
        faqs={},
    )
)