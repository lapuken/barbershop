document.querySelectorAll(".alert").forEach((alert) => {
    if (alert.classList.contains("alert-success")) {
        window.setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 3500);
    }
});
