
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


document.addEventListener("DOMContentLoaded", loadDashboard);

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
