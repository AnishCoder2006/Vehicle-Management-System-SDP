
const API_BASE = "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

async function fetchAPI(path) {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

async function fetchMaintenancePrediction(vehicleId) {
  try {
    return await fetchAPI(
      `/vehicles/${encodeURIComponent(vehicleId)}/maintenance-prediction`
    );
  } catch (error) {
    console.error(
      `Could not fetch maintenance prediction for vehicle ${vehicleId}:`,
      error
    );

    return null;
  }
}

function getList(data) {
  if (Array.isArray(data)) return data;

  if (data && typeof data === "object") {
    for (const key of ["vehicles", "drivers", "assignments", "services", "data", "results", "items"]) {
      if (Array.isArray(data[key])) return data[key];
    }
  }

  return [];
}

function getStatus(vehicle) {
  return String(vehicle.status || "unknown").toLowerCase();
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatStatus(status) {
  return status.replaceAll("_", " ");
}

function renderVehicles(vehicles) {
  const tbody = $("vehicleRows");

  if (!vehicles.length) {
    tbody.innerHTML = `
      <tr><td colspan="4" class="empty">
        No vehicle records found.
      </td></tr>`;
    return;
  }

  tbody.innerHTML = vehicles.map(vehicle => {
    const name = vehicle.name || vehicle.model || vehicle.vehicle_name || "Vehicle";
    const registration =
      vehicle.registration_number ||
      vehicle.registration ||
      vehicle.plate_number ||
      vehicle.license_plate ||
      vehicle.vehicle_number ||
      "—";

    const status = getStatus(vehicle);
    const id = vehicle.id ?? vehicle.vehicle_id ?? "—";
    const statusClass = ["available", "assigned", "in_service"].includes(status)
      ? status
      : "";

    return `
      <tr>
        <td><strong>${escapeHTML(name)}</strong></td>
        <td>${escapeHTML(registration)}</td>
        <td>
          <span class="status ${statusClass}">
            ${escapeHTML(formatStatus(status))}
          </span>
        </td>
        <td>#${escapeHTML(id)}</td>
        <td>
          <button
            type="button"
            class="prediction-btn"
            data-vehicle-id="${escapeHTML(id)}"
          >
            View prediction
          </button>
          <div
            class="prediction-result"
            id="prediction-${escapeHTML(id)}"
            aria-live="polite"
          ></div>
        </td>
      </tr>`;
  }).join("");
}

function renderServices(services) {
  const container = $("serviceList");

  if (!services.length) {
    container.innerHTML =
      `<p class="empty">No service records found.</p>`;
    return;
  }

  container.innerHTML = services.slice(0, 5).map(service => {
    return `
      <div class="service-item">
        <strong>${escapeHTML(service.service_type || "Vehicle Service")}</strong>
        <span>${escapeHTML(service.customer_name || "Customer unavailable")} · ${escapeHTML(service.status || "Unknown status")}</span>
        <span>Booked: ${escapeHTML(service.booked_date || "Not available")}</span>
      </div>`;
  }).join("");
}

function updateStats(vehicles, availableData, dueData, summaryData) {
  const summary = summaryData && typeof summaryData === "object"
    ? (summaryData.data || summaryData)
    : {};

  const availableList = getList(availableData);
  const dueList = getList(dueData);

  const total = vehicles.length;
  const available = availableList.length ||
    vehicles.filter(v => getStatus(v) === "available").length;
  const assigned = vehicles.filter(v => getStatus(v) === "assigned").length;
  const inService = vehicles.filter(v => getStatus(v) === "in_service").length;

  $("totalVehicles").textContent =
    summary.total_vehicles ?? summary.totalVehicles ?? total;

  $("availableVehicles").textContent =
    summary.available_vehicles ?? summary.availableVehicles ?? available;

  $("assignedVehicles").textContent =
    summary.assigned_vehicles ?? summary.assignedVehicles ?? assigned;

  $("dueVehicles").textContent =
    summary.due_for_service ?? summary.due_vehicles ?? dueList.length;

  $("snapshotAvailable").textContent = available;
  $("snapshotAssigned").textContent = assigned;
  $("snapshotService").textContent = inService;
}


async function loadDashboard() {
  $("connectionStatus").textContent = "Connecting to fleet API…";

  try {
    const [vehiclesResult, availableResult, servicesResult, summaryResult] =
      await Promise.allSettled([
        fetchAPI("/vehicles"),
        fetchAPI("/vehicles/available"),
        fetchAPI("/services"),
        fetchAPI("/stats/summary")
      ]);

    if (vehiclesResult.status === "rejected") {
      throw vehiclesResult.reason;
    }

    const vehicles = getList(vehiclesResult.value);

    const availableData = availableResult.status === "fulfilled"
      ? availableResult.value
      : [];

    const servicesData = servicesResult.status === "fulfilled"
      ? servicesResult.value
      : [];

    const summaryData = summaryResult.status === "fulfilled"
      ? summaryResult.value
      : {};

    renderVehicles(vehicles);
    renderServices(getList(servicesData));
    updateStats(vehicles, availableData, [], summaryData);

    $("connectionStatus").textContent =
      "Connected · Fleet data loaded successfully";

  } catch (error) {
    console.error("Could not load fleet data:", error);

    $("connectionStatus").textContent =
      "Could not connect. Check the backend and API URL.";

    $("vehicleRows").innerHTML = `
      <tr>
        <td colspan="4" class="empty">
          Unable to load vehicles. Start the backend and check the connection.
        </td>
      </tr>`;

    $("serviceList").innerHTML = `
      <p class="empty">Service data is currently unavailable.</p>`;
  }
}


document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
    loadAssignments();
    loadCosts();
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest(".prediction-btn");

  if (!button) return;

  const vehicleId = button.dataset.vehicleId;
  const resultElement = $(`prediction-${vehicleId}`);

  if (!resultElement) return;

  button.disabled = true;
  button.textContent = "Loading...";

  resultElement.textContent = "";

  try {
    const prediction = await fetchMaintenancePrediction(vehicleId);

    if (!prediction) {
      resultElement.textContent = "Prediction unavailable.";
      return;
    }

    const risk = String(prediction.maintenance_risk || "UNKNOWN")
      .toUpperCase();

    const percentage = Number(prediction.risk_percentage);

    resultElement.textContent = Number.isFinite(percentage)
      ? `${risk} · ${percentage.toFixed(2)}%`
      : risk;

    resultElement.classList.remove(
      "risk-low",
      "risk-medium",
      "risk-high"
    );

    const riskClass = {
      LOW: "risk-low",
      MEDIUM: "risk-medium",
      HIGH: "risk-high"
    }[risk];

    if (riskClass) {
      resultElement.classList.add(riskClass);
    }

  } catch (error) {
    console.error(error);
    resultElement.textContent = "Could not load prediction.";
  } finally {
    button.disabled = false;
    button.textContent = "View prediction";
  }
});

let assignmentRecords = [];
let assignmentVehicles = [];
let assignmentDrivers = [];

function formatAssignmentDate(value) {
    return value ? String(value).replace("T", " ").slice(0, 16) : "—";
}

async function loadAssignments() {
    const tbody = document.getElementById("assignmentRows");
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Loading assignments...</td></tr>`;

    try {
        const [assignments, vehicles, drivers] = await Promise.all([
            fetchAPI("/assignments"),
            fetchAPI("/vehicles"),
            fetchAPI("/drivers")
        ]);

        assignmentRecords = getList(assignments);
        assignmentVehicles = getList(vehicles);
        assignmentDrivers = getList(drivers);

        renderAssignments();
    } catch (error) {
        console.error("Could not load assignments:", error);
        tbody.innerHTML = `<tr><td colspan="7" class="empty">Could not load assignments. Check the backend.</td></tr>`;
    }
}

function renderAssignments() {
    const tbody = document.getElementById("assignmentRows");
    const filter = document.getElementById("assignmentFilter").value;

    const active = assignmentRecords.filter(item => item.is_active);
    const released = assignmentRecords.filter(item => !item.is_active);

    document.getElementById("totalAssignments").textContent = assignmentRecords.length;
    document.getElementById("activeAssignments").textContent = active.length;
    document.getElementById("releasedAssignments").textContent = released.length;

    const filtered = assignmentRecords.filter(item => {
        if (filter === "active") return item.is_active;
        if (filter === "released") return !item.is_active;
        return true;
    });

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">No assignments found.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(item => {
        const vehicle = assignmentVehicles.find(v => v.id === item.vehicle_id);
        const driver = assignmentDrivers.find(d => d.id === item.driver_id);

        const vehicleName = vehicle
            ? `${vehicle.make || ""} ${vehicle.model || ""} · ${vehicle.plate_number || ""}`.trim()
            : `Vehicle #${item.vehicle_id}`;

        const driverName = driver ? driver.name : `Driver #${item.driver_id}`;

        return `
            <tr>
                <td>#${escapeHTML(item.id)}</td>
                <td>${escapeHTML(vehicleName)}</td>
                <td>${escapeHTML(driverName)}</td>
                <td>${escapeHTML(formatAssignmentDate(item.assigned_at))}</td>
                <td>${escapeHTML(formatAssignmentDate(item.released_at))}</td>
                <td>
                    <span class="status ${item.is_active ? "assigned" : "available"}">
                        ${item.is_active ? "Active" : "Released"}
                    </span>
                </td>
                <td>
                    ${item.is_active
                        ? `<button type="button" class="release-assignment-btn" data-id="${escapeHTML(item.id)}">Release</button>`
                        : "—"}
                </td>
            </tr>
        `;
    }).join("");
}

document.getElementById("assignmentFilter").addEventListener("change", renderAssignments);

document.addEventListener("click", async event => {
    const button = event.target.closest(".release-assignment-btn");
    if (!button) return;

    const assignmentId = button.dataset.id;
    const message = document.getElementById("assignmentMessage");

    if (!confirm("Release this vehicle assignment?")) return;

    button.disabled = true;
    message.textContent = "Releasing assignment...";

    try {
        const response = await fetch(
            `${API_BASE}/assignments/${encodeURIComponent(assignmentId)}/release`,
            { method: "POST" }
        );

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        message.textContent = "Assignment released successfully!";
        await loadAssignments();
        await loadDashboard();
    } catch (error) {
        console.error(error);
        message.textContent = "Could not release assignment. Please try again.";
        button.disabled = false;
    }
});

let costRecords = [];

async function loadCosts() {
    const tbody = document.getElementById("costRows");
    tbody.innerHTML =
        `<tr><td colspan="5">Loading costs...</td></tr>`;

    try {
        const [costs, summary] = await Promise.all([
            fetchAPI("/costs"),
            fetchAPI("/costs/summary")
        ]);

        costRecords = getList(costs);

        document.getElementById("totalCost").textContent =
            Number(summary.grand_total || 0).toFixed(2);

        for (const category of ["fuel", "service", "parts"]) {
            const total = costRecords
                .filter(c => c.category === category)
                .reduce((sum, c) => sum + Number(c.amount || 0), 0);

            document.getElementById(category + "Cost").textContent =
                total.toFixed(2);
        }

        renderCosts();
    } catch (error) {
        console.error("Could not load costs:", error);
        tbody.innerHTML =
            `<tr><td colspan="5">Could not load cost records.</td></tr>`;
    }
}

function renderCosts() {
    const tbody = document.getElementById("costRows");
    const search = document.getElementById("costSearch").value.toLowerCase();
    const category = document.getElementById("costCategoryFilter").value;

    const filtered = costRecords.filter(c =>
        (category === "all" || c.category === category) &&
        `${c.description || ""} ${c.category} ${c.vehicle_id}`
            .toLowerCase().includes(search)
    );

    document.getElementById("costRecordCount").textContent =
        `${filtered.length} records`;

    if (!filtered.length) {
        tbody.innerHTML =
            `<tr><td colspan="5">No matching cost records.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(c => `
        <tr>
            <td>#${escapeHTML(c.vehicle_id)}</td>
            <td>${escapeHTML(c.category)}</td>
            <td>${Number(c.amount).toFixed(2)}</td>
            <td>${escapeHTML(c.log_date)}</td>
            <td>${escapeHTML(c.description || "—")}</td>
        </tr>
    `).join("");
}

document.getElementById("costSearch")
    .addEventListener("input", renderCosts);

document.getElementById("costCategoryFilter")
    .addEventListener("change", renderCosts);

document.getElementById("refreshCosts")
    .addEventListener("click", loadCosts);

async function loadCostCharts() {
    try {
        const summary = await fetchAPI("/costs/summary");

        const monthlyContainer = document.getElementById("monthlyCostChart");
        const vehicleContainer = document.getElementById("vehicleCostBreakdown");

        monthlyContainer.innerHTML = `
            <div class="cost-bars">
                ${Object.entries(summary.by_month || {}).map(([month, amount]) => `
                    <div class="cost-bar-row">
                        <span>${escapeHTML(month)}</span>
                        <div class="cost-bar-track">
                            <div class="cost-bar-fill"
                                 style="width:${Math.max(0, Number(amount)) / Math.max(1, ...Object.values(summary.by_month).map(Number)) * 100}%">
                            </div>
                        </div>
                        <strong>₹${Number(amount).toFixed(2)}</strong>
                    </div>
                `).join("")}
            </div>
        `;

        const vehicles = Object.entries(summary.by_vehicle || {})
            .sort((a, b) => Number(b[1]) - Number(a[1]));

        vehicleContainer.innerHTML = `
            <div class="cost-bars">
                ${vehicles.map(([vehicleId, amount]) => `
                    <div class="cost-bar-row">
                        <span>Vehicle #${escapeHTML(vehicleId)}</span>
                        <div class="cost-bar-track">
                            <div class="cost-bar-fill"
                                 style="width:${Number(amount) / Math.max(1, ...vehicles.map(v => Number(v[1]))) * 100}%">
                            </div>
                        </div>
                        <strong>₹${Number(amount).toFixed(2)}</strong>
                    </div>
                `).join("")}
            </div>
        `;
    } catch (error) {
        console.error("Could not load cost charts:", error);
        document.getElementById("monthlyCostChart").textContent =
            "Monthly chart unavailable.";
        document.getElementById("vehicleCostBreakdown").textContent =
            "Vehicle chart unavailable.";
    }
}

document.addEventListener("DOMContentLoaded", loadCostCharts);

async function loadCostVehicles() {
    const vehicleSelect = document.getElementById("costVehicle");

    try {
        const response = await fetchAPI("/vehicles");
        const vehicles = getList(response);

        vehicleSelect.innerHTML =
            '<option value="">Select a vehicle</option>';

        vehicles.forEach(vehicle => {
            const option = document.createElement("option");
            option.value = vehicle.id;
            option.textContent =
                `${vehicle.name || vehicle.model || "Vehicle"} — ${vehicle.registration_number || vehicle.license_plate || vehicle.id}`;
            vehicleSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Could not load vehicles:", error);
        vehicleSelect.innerHTML =
            '<option value="">Could not load vehicles</option>';
    }
}

document.addEventListener("DOMContentLoaded", loadCostVehicles);

document.getElementById("costForm")
    .addEventListener("submit", async event => {
        event.preventDefault();

        const form = event.target;
        const message = document.getElementById("costRecordCount");
        const submitButton = form.querySelector('button[type="submit"]');

        const expense = {
            vehicle_id: Number(form.querySelector('[name="vehicle_id"]').value),
            category: form.querySelector('[name="category"]').value,
            amount: Number(form.querySelector('[name="amount"]').value),
            log_date: form.querySelector('[name="log_date"]').value,
            description: form.querySelector('[name="description"]').value
        };

        submitButton.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/costs`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(expense)
            });

            if (!response.ok) {
                throw new Error(await response.text());
            }

            form.reset();
            await loadCosts();
            await loadCostCharts();

            message.textContent = "Expense saved successfully!";
        } catch (error) {
            console.error("Could not save expense:", error);
            message.textContent = "Could not save expense. Check the form fields.";
        } finally {
            submitButton.disabled = false;
        }
    });

document.getElementById("costForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const form = event.target;
    const button = document.getElementById("saveCostButton");

    const expense = {
        vehicle_id: Number(form.elements["vehicle_id"].value),
        category: form.elements["category"].value,
        amount: Number(form.elements["amount"].value),
        log_date: form.elements["log_date"].value || null,
        description: form.elements["description"].value.trim() || null
    };

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        await fetchAPI("/costs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(expense)
        });

        form.reset();
        await loadCosts();
        await loadCostCharts();

        alert("Expense added successfully!");
    } catch (error) {
        console.error("Could not save expense:", error);
        alert("Could not save expense. Please check the form and try again.");
    } finally {
        button.disabled = false;
        button.textContent = "+ Add expense";
    }
});
