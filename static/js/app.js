const state = { region: "all", diet: "all" };

document.querySelectorAll("[data-filter-group]").forEach((group) => {
  group.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    group.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state[group.dataset.filterGroup] = button.dataset.value;
    filterRecipes();
  });
});

function filterRecipes() {
  let shown = 0;
  document.querySelectorAll(".recipe-card").forEach((card) => {
    const matchesRegion = state.region === "all" || card.dataset.region === state.region;
    const matchesDiet = state.diet === "all" || card.dataset.diet === state.diet;
    card.classList.toggle("is-hidden", !(matchesRegion && matchesDiet));
    if (matchesRegion && matchesDiet) shown += 1;
  });
  const empty = document.querySelector(".empty-state");
  if (empty) empty.hidden = shown !== 0;
}

const observer = new IntersectionObserver(
  (entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
      observer.unobserve(entry.target);
    }
  }),
  { threshold: 0.12 }
);
document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));

document.querySelectorAll('input[inputmode="numeric"]').forEach((input) => {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/[^0-9 ]/g, "");
  });
});

const reviewsToggle = document.querySelector(".reviews-toggle");
if (reviewsToggle) {
  reviewsToggle.addEventListener("click", () => {
    const expanded = reviewsToggle.getAttribute("aria-expanded") === "true";
    document.querySelectorAll(".review-extra").forEach((review) => {
      review.hidden = expanded;
    });
    reviewsToggle.setAttribute("aria-expanded", String(!expanded));
    reviewsToggle.querySelector("span").textContent = expanded
      ? `Vezi toate recenziile (+${reviewsToggle.dataset.moreCount})`
      : "Arată doar ultimele 5";
    reviewsToggle.querySelector("b").textContent = expanded ? "↓" : "↑";
  });
}
