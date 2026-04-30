document.addEventListener("DOMContentLoaded", () => {
    window.showLuxuryToast = (message, type = "info") => {
        const stack = document.getElementById("toast-stack") || (() => {
            const element = document.createElement("div");
            element.id = "toast-stack";
            element.className = "luxury-toast-stack";
            document.body.appendChild(element);
            return element;
        })();

        const toast = document.createElement("div");
        toast.className = `luxury-toast luxury-toast-${type}`;
        toast.innerHTML = `<span>${message}</span><button type="button" class="luxury-toast-close" aria-label="Dismiss notification">&times;</button>`;
        stack.appendChild(toast);

        toast.querySelector(".luxury-toast-close")?.addEventListener("click", () => toast.remove());
        window.setTimeout(() => toast.remove(), 3200);
    };

    document.querySelectorAll(".luxury-toast-close").forEach((button) => {
        button.addEventListener("click", () => {
            button.closest(".luxury-toast")?.remove();
        });
    });

    document.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
        const trigger = dropdown.querySelector("[data-dropdown-trigger]");
        trigger?.addEventListener("click", (event) => {
            event.preventDefault();
            dropdown.classList.toggle("is-open");
        });

        document.addEventListener("click", (event) => {
            if (!dropdown.contains(event.target)) {
                dropdown.classList.remove("is-open");
            }
        });
    });

    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.parentElement?.querySelector("input");
            if (!input) return;
            const visible = input.type === "password";
            input.type = visible ? "text" : "password";
            button.classList.toggle("is-visible", visible);
            button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
        });
    });

    document.querySelectorAll("[data-loading-form]").forEach((form) => {
        form.addEventListener("submit", () => {
            const paymentField = form.querySelector(".payment-dropdown");
            if (paymentField) return;

            const button = form.querySelector("[data-loading-button]");
            if (!button) return;
            button.classList.add("is-loading");
            button.setAttribute("disabled", "disabled");
        });
    });

    const authModal = document.getElementById("auth-modal");
    const authTitle = document.getElementById("auth-modal-title");
    const authMessage = document.getElementById("auth-modal-message");
    const loginLink = document.getElementById("auth-modal-login");
    const signupLink = document.getElementById("auth-modal-signup");
    const modalBaseUrl = document.body.dataset.authModalUrl;

    const closeAuthModal = () => {
        if (authModal) authModal.hidden = true;
    };

    window.openAuthRequiredModal = async (nextUrl, fallbackMessage) => {
        if (!authModal) {
            window.location.href = `/login/?next=${encodeURIComponent(nextUrl)}`;
            return;
        }

        try {
            const response = await fetch(`${modalBaseUrl}?next=${encodeURIComponent(nextUrl)}`);
            const data = await response.json();
            authTitle.textContent = data.title;
            authMessage.textContent = data.message || fallbackMessage;
            loginLink.href = data.login_url;
            signupLink.href = data.signup_url;
            authModal.hidden = false;
        } catch (error) {
            window.location.href = `/login/?next=${encodeURIComponent(nextUrl)}`;
        }
    };

    document.querySelector(".luxury-modal-close")?.addEventListener("click", closeAuthModal);
    authModal?.addEventListener("click", (event) => {
        if (event.target === authModal) closeAuthModal();
    });

    const noticeModal = document.getElementById("premium-notice-modal");
    const noticeTitle = document.getElementById("premium-notice-title");
    const noticeMessage = document.getElementById("premium-notice-message");
    const noticeConfirm = document.getElementById("premium-notice-confirm");
    const noticeCancel = document.getElementById("premium-notice-cancel");
    const noticeClose = document.querySelector(".premium-notice-close");

    const closeNoticeModal = () => {
        if (noticeModal) noticeModal.hidden = true;
    };

    window.premiumNoticeModal = {
        open({ title, message }) {
            if (!noticeModal) return;
            noticeTitle.textContent = title || "Please select a size before continuing";
            noticeMessage.textContent = message || "Choose your preferred size to continue.";
            noticeModal.hidden = false;
        },
        close: closeNoticeModal,
    };

    [noticeConfirm, noticeCancel, noticeClose].forEach((button) => {
        button?.addEventListener("click", closeNoticeModal);
    });

    noticeModal?.addEventListener("click", (event) => {
        if (event.target === noticeModal) closeNoticeModal();
    });

    document.querySelectorAll(".guest-wishlist-link").forEach((link) => {
        link.addEventListener("click", (event) => {
            if (document.body.dataset.authenticated === "true") return;
            event.preventDefault();
            window.openAuthRequiredModal(link.dataset.nextUrl || "/wishlist/", "Sign in to save favourites.");
        });
    });

    document.querySelectorAll(".wishlist-btn").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();

            const productId = button.dataset.id;
            const nextUrl = button.dataset.productUrl || window.location.pathname;

            try {
                const response = await fetch(`/wishlist/toggle/${productId}/`);
                const data = await response.json();

                if (!data.success && data.requires_auth) {
                    window.openAuthRequiredModal(nextUrl, data.message || "Sign in to save favourites.");
                    return;
                }

                if (!data.success) {
                    window.showLuxuryToast("We couldn't update your wishlist.", "error");
                    return;
                }

                button.classList.toggle("active", data.in_wishlist);
                button.classList.add("is-pulsing");
                window.setTimeout(() => button.classList.remove("is-pulsing"), 420);

                const icon = button.querySelector("svg");
                if (icon) {
                    icon.setAttribute("fill", data.in_wishlist ? "currentColor" : "none");
                }

                window.showLuxuryToast(data.message || (data.in_wishlist ? "Added to wishlist." : "Removed from wishlist."), "success");
            } catch (error) {
                window.showLuxuryToast("We couldn't update your wishlist.", "error");
            }
        });
    });

    if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target) {
            window.setTimeout(() => {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
        }
    }

    document.querySelectorAll("[data-product-gallery]").forEach((gallery) => {
        const mainImage = gallery.querySelector("[data-gallery-main]");
        const thumbs = Array.from(gallery.querySelectorAll("[data-gallery-thumb]"));
        const prev = gallery.querySelector("[data-gallery-prev]");
        const next = gallery.querySelector("[data-gallery-next]");
        if (!mainImage || !thumbs.length) return;

        let activeIndex = thumbs.findIndex((thumb) => thumb.classList.contains("active"));
        if (activeIndex < 0) activeIndex = 0;

        const setImage = (index) => {
            const boundedIndex = (index + thumbs.length) % thumbs.length;
            const selectedThumb = thumbs[boundedIndex];
            if (!selectedThumb) return;

            thumbs.forEach((thumb) => thumb.classList.remove("active"));
            selectedThumb.classList.add("active");
            mainImage.classList.add("is-switching");

            window.setTimeout(() => {
                mainImage.src = selectedThumb.dataset.imageUrl;
                mainImage.alt = selectedThumb.dataset.imageAlt || "";
                mainImage.classList.remove("is-switching");
            }, 140);

            activeIndex = boundedIndex;
        };

        thumbs.forEach((thumb, index) => {
            thumb.addEventListener("click", () => setImage(index));
        });

        prev?.addEventListener("click", () => setImage(activeIndex - 1));
        next?.addEventListener("click", () => setImage(activeIndex + 1));

        let touchStartX = 0;
        gallery.addEventListener("touchstart", (event) => {
            touchStartX = event.changedTouches[0].screenX;
        }, { passive: true });

        gallery.addEventListener("touchend", (event) => {
            const touchEndX = event.changedTouches[0].screenX;
            const diff = touchStartX - touchEndX;
            if (Math.abs(diff) < 40) return;
            setImage(activeIndex + (diff > 0 ? 1 : -1));
        }, { passive: true });
    });

    document.querySelectorAll("[data-checkout-root]").forEach((checkoutRoot) => {
        const form = checkoutRoot.querySelector("[data-checkout-form]");
        const paymentField = form?.querySelector(".payment-dropdown");
        const razorpayButton = checkoutRoot.querySelector("[data-razorpay-button]");
        const subtotalDisplay = checkoutRoot.querySelector("[data-subtotal-display]");
        const shippingDisplay = checkoutRoot.querySelector("[data-shipping-display]");
        const totalDisplay = checkoutRoot.querySelector("[data-total-display]");
        const deliveryPill = checkoutRoot.querySelector("[data-delivery-pill]");
        const summary = checkoutRoot.querySelector("[data-checkout-summary]");
        const shippingFields = Array.from(form?.querySelectorAll("input[name='shipping_method']") || []);

        if (!form || !paymentField || !razorpayButton || !summary) return;

        const standardShipping = Number.parseFloat(summary.dataset.standardShipping || "0");
        const expressShipping = Number.parseFloat(summary.dataset.expressShipping || "249");
        const subtotal = Number.parseFloat(summary.dataset.subtotal || "0");

        const formatCurrency = (value) => `₹${value.toFixed(2)}`;
        const formatDeliveryText = (shippingMethod) => {
            const target = new Date();
            target.setDate(target.getDate() + (shippingMethod === "Express" ? 3 : 6));
            return `Estimated delivery by ${target.toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
            })}`;
        };

        const selectedShippingMethod = () => {
            return shippingFields.find((field) => field.checked)?.value || "Standard";
        };

        const recalculateTotals = () => {
            const shippingMethod = selectedShippingMethod();
            const shippingFee = shippingMethod === "Express" ? expressShipping : standardShipping;
            const total = subtotal + shippingFee;

            if (shippingDisplay) {
                shippingDisplay.textContent = shippingFee > 0 ? formatCurrency(shippingFee) : "Complimentary";
            }
            if (totalDisplay) {
                totalDisplay.textContent = formatCurrency(total);
            }
            if (subtotalDisplay) {
                subtotalDisplay.textContent = formatCurrency(subtotal);
            }
            if (deliveryPill) {
                deliveryPill.textContent = formatDeliveryText(shippingMethod);
            }
        };

        const updateRazorpayState = () => {
            razorpayButton.disabled = false;
            razorpayButton.classList.remove("is-disabled");
        };

        shippingFields.forEach((field) => {
            field.addEventListener("change", recalculateTotals);
        });

        paymentField.addEventListener("change", updateRazorpayState);

        razorpayButton.addEventListener("click", async () => {
            const submitButton = form.querySelector("[data-loading-button]");
            submitButton?.classList.remove("is-loading");
            submitButton?.removeAttribute("disabled");

            try {
                const response = await fetch(form.dataset.createOrderUrl, {
                    method: "POST",
                    body: new FormData(form),
                });
                const data = await response.json();

                if (!response.ok || !data.success) {
                    window.showLuxuryToast(data.message || "Unable to initiate payment.", "error");
                    return;
                }

                const options = {
                    key: data.key,
                    amount: data.amount,
                    currency: data.currency,
                    name: data.name,
                    description: data.description,
                    image: data.image || undefined,
                    order_id: data.order_id,
                    prefill: data.prefill,
                    notes: data.notes,
                    theme: {
                        color: "#b79b69",
                    },
                    handler: async function (paymentResponse) {
                        try {
                            const verifyResponse = await fetch(form.dataset.verifyOrderUrl, {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                    "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
                                },
                                body: JSON.stringify(paymentResponse),
                            });
                            const verifyData = await verifyResponse.json();

                            if (!verifyResponse.ok || !verifyData.success) {
                                window.showLuxuryToast(verifyData.message || "Payment verification failed.", "error");
                                return;
                            }

                            window.location.href = verifyData.redirect_url;
                        } catch (error) {
                            window.showLuxuryToast("Payment verification failed.", "error");
                        }
                    },
                    modal: {
                        ondismiss: function () {
                            window.showLuxuryToast("Payment window closed before completion.", "info");
                        },
                    },
                };

                const razorpay = new Razorpay(options);
                razorpay.on("payment.failed", function (event) {
                    const message = event.error?.description || "Payment failed. Please try again.";
                    window.showLuxuryToast(message, "error");
                });
                razorpay.open();
            } catch (error) {
                window.showLuxuryToast("Unable to initiate payment.", "error");
            }
        });

        recalculateTotals();
        updateRazorpayState();
    });
});
