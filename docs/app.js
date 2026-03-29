const budgetInput = document.getElementById("budget");
const budgetValue = document.getElementById("budget-value");
const plannerForm = document.getElementById("planner-form");
const itineraryDays = document.getElementById("itinerary-days");
const itineraryTitle = document.getElementById("itinerary-title");
const itinerarySummary = document.getElementById("itinerary-summary");

const cityPlans = {
  Riyadh: [
    "Visit a landmark museum and start with a city breakfast.",
    "Spend the afternoon shopping and exploring a major boulevard.",
    "Close the day with family dining and evening entertainment.",
    "Add a culture-focused stop with cafes and photo moments.",
    "Wrap up with a relaxed park or attraction visit."
  ],
  Jeddah: [
    "Begin with a waterfront walk and breakfast by the sea.",
    "Explore city cafés, shopping areas, and a relaxed lunch spot.",
    "Enjoy an evening corniche session with casual dining.",
    "Mix in art, old streets, and food discoveries.",
    "Finish with a sunset stop and memorable photos."
  ],
  AlUla: [
    "Start with a scenic heritage site and quiet morning views.",
    "Move into a desert landscape experience and photography break.",
    "Plan a relaxed evening with local dining and stargazing.",
    "Add another heritage-focused stop for a deeper cultural day.",
    "Close with a panoramic viewpoint and a slow-paced finale."
  ],
  Abha: [
    "Open the trip with mountain scenery and cool-air sightseeing.",
    "Spend the day on nature walks and café stops.",
    "Keep the evening light with family-friendly dining.",
    "Add local markets and scenic viewpoints.",
    "Finish with a calm final day in green surroundings."
  ],
  NEOM: [
    "Kick off with bold scenery and a modern adventure mood.",
    "Dedicate the afternoon to exploration and photo-rich stops.",
    "Use the evening for premium dining and a slow reset.",
    "Add another active day with dramatic surroundings.",
    "End with a final scenic route and reflection stop."
  ]
};

function renderBudget() {
  if (!budgetInput || !budgetValue) {
    return;
  }
  budgetValue.textContent = `${budgetInput.value} SAR`;
}

function renderItinerary(city, days, tripType, interest, budget) {
  const plan = cityPlans[city] || cityPlans.Riyadh;
  const totalDays = Number(days);
  itineraryTitle.textContent = `${city} ${tripType.toLowerCase()} trip`;
  itinerarySummary.textContent = `${totalDays}-day plan focused on ${interest.toLowerCase()} with an estimated budget of ${budget} SAR.`;
  itineraryDays.innerHTML = "";

  for (let day = 1; day <= totalDays; day += 1) {
    const card = document.createElement("article");
    card.className = "itinerary-day";
    card.innerHTML = `
      <span class="day-badge">Day ${day}</span>
      <h3>${city} plan ${day}</h3>
      <p>${plan[(day - 1) % plan.length]}</p>
    `;
    itineraryDays.appendChild(card);
  }
}

if (budgetInput) {
  budgetInput.addEventListener("input", renderBudget);
  renderBudget();
}

if (plannerForm) {
  plannerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    renderItinerary(
      plannerForm.city.value,
      plannerForm.days.value,
      plannerForm.tripType.value,
      plannerForm.interest.value,
      plannerForm.budget.value
    );
  });

  renderItinerary("Riyadh", "3", "Family", "Culture", "1800");
}
