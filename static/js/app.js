document.querySelectorAll(".alert").forEach((alert) => {
    if (alert.classList.contains("alert-success")) {
        window.setTimeout(() => {
            if (window.bootstrap?.Alert) {
                const bsAlert = window.bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
                return;
            }
            alert.remove();
        }, 3500);
    }
});
