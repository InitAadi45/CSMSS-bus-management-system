/* 
   CSMSS Bus Management System Client-Side Scripts
   Handles interactive animations, simulated payments, live searches, and alerts.
*/

document.addEventListener('DOMContentLoaded', function () {
    // 1. Navbar Scrolled Styling
    const navbar = document.querySelector('.navbar-glass');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // 2. Alert/Toast Auto-dismiss
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Smooth fade out using Bootstrap
            if (typeof bootstrap !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.display = 'none';
            }
        }, 5000);
    });

    // 3. Client-Side Quick Table Filter (Search)
    const searchInputs = document.querySelectorAll('.table-search-input');
    searchInputs.forEach(function (input) {
        const targetTableId = input.getAttribute('data-target-table');
        const table = document.getElementById(targetTableId);
        
        if (table) {
            input.addEventListener('keyup', function () {
                const value = this.value.toLowerCase();
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(function (row) {
                    const text = row.textContent.toLowerCase();
                    if (text.indexOf(value) > -1) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }
    });

    // 4. Payment Gateway Simulator
    const selectPassButtons = document.querySelectorAll('.select-pass-btn');
    const paymentModal = document.getElementById('paymentModal');
    
    if (selectPassButtons.length > 0 && paymentModal) {
        const modalPassType = document.getElementById('modalPassType');
        const modalPrice = document.getElementById('modalPrice');
        const modalPassTypeInput = document.getElementById('modalPassTypeInput');
        const modalPriceInput = document.getElementById('modalPriceInput');
        
        // Pass option click
        selectPassButtons.forEach(button => {
            button.addEventListener('click', function () {
                const passType = this.getAttribute('data-pass-type');
                const price = this.getAttribute('data-price');
                
                modalPassType.textContent = passType + " Pass";
                modalPrice.textContent = "₹" + price;
                modalPassTypeInput.value = passType;
                modalPriceInput.value = price;
            });
        });

        // Toggle payment options inside modal
        const payBtns = document.querySelectorAll('.payment-method-btn');
        const selectedMethodInput = document.getElementById('paymentMethodInput');
        
        payBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                payBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                selectedMethodInput.value = this.getAttribute('data-method');
            });
        });

        // Submit mock payment form
        const paymentForm = document.getElementById('simulatedPaymentForm');
        const processButton = document.getElementById('processPaymentBtn');
        const paySpinner = document.getElementById('paymentSpinner');
        
        if (paymentForm) {
            paymentForm.addEventListener('submit', function (e) {
                e.preventDefault();
                
                // Show loading state
                processButton.disabled = true;
                paySpinner.classList.remove('d-none');
                processButton.textContent = "Processing Transaction...";
                
                const formData = new FormData(paymentForm);
                
                // Simulate network latency of 2 seconds
                setTimeout(() => {
                    fetch('/student/process-payment', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        paySpinner.classList.add('d-none');
                        
                        if (data.success) {
                            // Show success modal or direct redirect
                            showLocalToast("Payment Successful!", "success");
                            setTimeout(() => {
                                window.location.href = `/student/receipt/${data.receipt_id}`;
                            }, 1000);
                        } else {
                            showLocalToast("Transaction Failed: " + data.message, "danger");
                            processButton.disabled = false;
                            processButton.textContent = "Confirm & Pay";
                        }
                    })
                    .catch(err => {
                        paySpinner.classList.add('d-none');
                        showLocalToast("Network error. Please try again.", "danger");
                        processButton.disabled = false;
                        processButton.textContent = "Confirm & Pay";
                    });
                }, 2000);
            });
        }
    }
});

// Toast Creator Helper
function showLocalToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) {
        // Create container if not exists
        const toastCont = document.createElement('div');
        toastCont.id = 'toastContainer';
        toastCont.style.position = 'fixed';
        toastCont.style.top = '24px';
        toastCont.style.right = '24px';
        toastCont.style.zIndex = '1060';
        document.body.appendChild(toastCont);
    }
    
    const toast = document.createElement('div');
    toast.className = `alert alert-toast alert-toast-${type} d-flex align-items-center justify-content-between p-3 mb-2`;
    toast.role = 'alert';
    
    let iconClass = 'fa-check-circle text-success';
    if (type === 'danger') iconClass = 'fa-exclamation-circle text-danger';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle text-warning';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <i class="fas ${iconClass}"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" style="font-size:0.8rem;" onclick="this.parentElement.remove()"></button>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4500);
}
