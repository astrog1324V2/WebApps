const macroConfig = [
  { key: "calories", label: "Calories", type: "calories" },
  { key: "protein_g", label: "Protein (g)", type: "grams" },
  { key: "carbs_g", label: "Carbs (g)", type: "grams" },
  { key: "fats_g", label: "Fats (g)", type: "grams" },
  { key: "sugars_g", label: "Sugars (g)", type: "grams" },
  { key: "fibre_g", label: "Fibre (g)", type: "grams" },
];

const state = {
  ingredients: [],
  nextId: 1,
};

const scanForm = document.querySelector("#scan-form");
const fileInput = document.querySelector("#label-image");
const scanStatus = document.querySelector("#scan-status");
const ingredientList = document.querySelector("#ingredient-list");
const ingredientSummary = document.querySelector("#ingredient-summary");
const totalGrid = document.querySelector("#total-grid");
const copyStatus = document.querySelector("#copy-status");
const copyTotalButton = document.querySelector("#copy-total");
const clearMealButton = document.querySelector("#clear-meal");
const template = document.querySelector("#ingredient-template");

function parseOptionalNumber(rawValue) {
  if (rawValue === "" || rawValue === null || rawValue === undefined) {
    return null;
  }
  const value = Number(rawValue);
  return Number.isFinite(value) ? value : null;
}

function formatGrams(value) {
  const rounded = Math.round(value * 10) / 10;
  if (Number.isInteger(rounded)) {
    return String(rounded);
  }
  return rounded.toFixed(1);
}

function formatCalories(value) {
  return String(Math.round(value));
}

function formatClockTime() {
  const now = new Date();
  let hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const suffix = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  return `${String(hours).padStart(2, "0")}:${minutes} ${suffix}`;
}

function buildTsvRow(values) {
  return [
    formatCalories(values.calories),
    formatGrams(values.protein_g),
    formatGrams(values.carbs_g),
    formatGrams(values.fats_g),
    formatGrams(values.sugars_g),
    formatGrams(values.fibre_g),
    formatClockTime(),
  ].join("\t");
}

function computeScaledIngredient(ingredient) {
  const servingGrams = parseOptionalNumber(ingredient.serving_grams);
  const consumedGrams = parseOptionalNumber(ingredient.consumed_grams);
  const errors = [];

  if (!(servingGrams > 0)) {
    errors.push("Serving grams must be greater than 0.");
  }
  if (!(consumedGrams >= 0)) {
    errors.push("Consumed grams must be 0 or greater.");
  }

  const scaled = {};
  for (const macro of macroConfig) {
    const value = parseOptionalNumber(ingredient[macro.key]);
    if (value === null || value < 0) {
      errors.push(`${macro.label} is missing.`);
      scaled[macro.key] = null;
      continue;
    }
    if (servingGrams > 0 && consumedGrams >= 0) {
      scaled[macro.key] = value * (consumedGrams / servingGrams);
    } else {
      scaled[macro.key] = null;
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    scaled,
  };
}

function computeTotals() {
  const totals = {
    calories: 0,
    protein_g: 0,
    carbs_g: 0,
    fats_g: 0,
    sugars_g: 0,
    fibre_g: 0,
  };

  let validCount = 0;
  let invalidCount = 0;

  for (const ingredient of state.ingredients) {
    const result = computeScaledIngredient(ingredient);
    ingredient._result = result;
    if (result.valid) {
      validCount += 1;
      for (const macro of macroConfig) {
        totals[macro.key] += result.scaled[macro.key];
      }
    } else {
      invalidCount += 1;
    }
  }

  return { totals, validCount, invalidCount };
}

function renderTotals() {
  const { totals, validCount, invalidCount } = computeTotals();
  totalGrid.innerHTML = "";

  for (const macro of macroConfig) {
    const pill = document.createElement("div");
    pill.className = "macro-pill";
    const value = macro.type === "calories"
      ? formatCalories(totals[macro.key])
      : formatGrams(totals[macro.key]);
    pill.innerHTML = `<strong>${value}</strong><span>${macro.label}</span>`;
    totalGrid.appendChild(pill);
  }

  const timePill = document.createElement("div");
  timePill.className = "macro-pill";
  timePill.innerHTML = `<strong>${formatClockTime()}</strong><span>Time</span>`;
  totalGrid.appendChild(timePill);

  if (state.ingredients.length === 0) {
    ingredientSummary.textContent = "No ingredients yet.";
    copyStatus.textContent = "";
    copyTotalButton.disabled = true;
    return;
  }

  ingredientSummary.textContent = `${validCount} ready, ${invalidCount} need fixes.`;
  copyTotalButton.disabled = !(validCount > 0 && invalidCount === 0);
  if (invalidCount > 0) {
    copyStatus.textContent = "Fix incomplete ingredients before copying the total.";
  } else {
    copyStatus.textContent = "";
  }
}

function renderWarnings(target, messages) {
  target.innerHTML = "";
  messages.forEach((message) => {
    const chip = document.createElement("span");
    chip.className = "warning-chip";
    chip.textContent = message;
    target.appendChild(chip);
  });
}

function updateIngredientCard(card, ingredient, index) {
  card.querySelector(".ingredient-index").textContent = `Ingredient ${index + 1}`;

  const servingGrams = parseOptionalNumber(ingredient.serving_grams);
  const servingText = servingGrams > 0
    ? `${ingredient.serving_label_text} | Current serving: ${formatGrams(servingGrams)} g`
    : ingredient.serving_label_text;
  card.querySelector(".ingredient-serving").textContent = servingText;

  const warnings = [...ingredient.warnings, ...ingredient._result.errors];
  renderWarnings(card.querySelector(".warnings"), warnings);

  const subtotalElement = card.querySelector(".ingredient-subtotal");
  if (ingredient._result.valid) {
    subtotalElement.textContent = buildTsvRow(ingredient._result.scaled);
  } else {
    subtotalElement.textContent = "Complete the fields to enable copy.";
  }

  card.querySelector(".copy-single").disabled = !ingredient._result.valid;
}

function renderIngredients() {
  ingredientList.innerHTML = "";

  state.ingredients.forEach((ingredient, index) => {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".ingredient-card");

    const nameInput = fragment.querySelector(".ingredient-name");
    nameInput.value = ingredient.name;
    nameInput.addEventListener("input", (event) => {
      ingredient.name = event.target.value || `Ingredient ${index + 1}`;
    });

    const fieldMap = {
      ".field-serving-grams": "serving_grams",
      ".field-consumed-grams": "consumed_grams",
      ".field-calories": "calories",
      ".field-protein": "protein_g",
      ".field-carbs": "carbs_g",
      ".field-fats": "fats_g",
      ".field-sugars": "sugars_g",
      ".field-fibre": "fibre_g",
    };

    for (const [selector, key] of Object.entries(fieldMap)) {
      const input = fragment.querySelector(selector);
      input.value = ingredient[key] ?? "";
      input.addEventListener("input", (event) => {
        ingredient[key] = event.target.value;
        renderTotals();
        updateIngredientCard(card, ingredient, index);
      });
    }

    const copySingleButton = fragment.querySelector(".copy-single");
    copySingleButton.addEventListener("click", async () => {
      await navigator.clipboard.writeText(buildTsvRow(ingredient._result.scaled));
      copyStatus.textContent = `${ingredient.name} copied.`;
      renderTotals();
    });

    fragment.querySelector(".remove-ingredient").addEventListener("click", () => {
      state.ingredients = state.ingredients.filter((item) => item.id !== ingredient.id);
      renderIngredients();
      renderTotals();
    });

    updateIngredientCard(card, ingredient, index);
    ingredientList.appendChild(fragment);
  });
}

function addIngredient(extraction) {
  state.ingredients.push({
    id: state.nextId++,
    name: `Ingredient ${state.ingredients.length + 1}`,
    serving_label_text: extraction.serving_label_text,
    serving_grams: extraction.serving_grams,
    consumed_grams: extraction.serving_grams,
    calories: extraction.calories ?? "",
    protein_g: extraction.protein_g ?? "",
    carbs_g: extraction.carbs_g ?? "",
    fats_g: extraction.fats_g ?? "",
    sugars_g: extraction.sugars_g ?? "",
    fibre_g: extraction.fibre_g ?? "",
    warnings: extraction.warnings || [],
    _result: { valid: false, errors: [], scaled: {} },
  });
  renderTotals();
  renderIngredients();
  renderTotals();
}

scanForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) {
    scanStatus.textContent = "Choose a label photo first.";
    return;
  }

  scanStatus.textContent = "Analyzing label...";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/extract-label", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Label extraction failed.");
    }
    addIngredient(payload.extraction);
    scanStatus.textContent = "Ingredient added.";
    scanForm.reset();
  } catch (error) {
    scanStatus.textContent = error.message;
  }
});

copyTotalButton.addEventListener("click", async () => {
  const { totals, invalidCount, validCount } = computeTotals();
  if (!(validCount > 0) || invalidCount > 0) {
    copyStatus.textContent = "Fix incomplete ingredients before copying the total.";
    return;
  }
  await navigator.clipboard.writeText(buildTsvRow(totals));
  copyStatus.textContent = "Meal total copied.";
  renderTotals();
});

clearMealButton.addEventListener("click", () => {
  state.ingredients = [];
  renderIngredients();
  renderTotals();
});

renderTotals();
