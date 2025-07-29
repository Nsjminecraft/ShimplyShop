// This is your test secret API key.
const stripe = Stripe("pk_test_51RZHmmRhhhXJ2E0GQWTPH9iJyhQnIFyXFol2EcB2KwHuYJtQwEn0U0XNKyHdRHesU1ljlwJLFibGzRJrTQTmtHab00AuvwlVSE");

initialize();

// Create a Checkout Session
async function initialize() {
  const fetchClientSecret = async () => {
    const response = await fetch("/create-checkout-session", {
      method: "POST",
    });
    const { clientSecret } = await response.json();
    return clientSecret;
  };

  const checkout = await stripe.initEmbeddedCheckout({
    fetchClientSecret,
  });

  // Mount Checkout
  checkout.mount('#checkout');
}