const e2eUsers = require("../fixtures/users/e2e-users.json");

function validateLoggedInUser(email) {
	return cy
		.request({
			method: "GET",
			url: "/api/method/frappe.auth.get_logged_user",
			failOnStatusCode: false,
		})
		.then((response) => {
			expect(response.status).to.eq(200);
			expect(response.body && response.body.message).to.eq(email);
		});
}

function loginViaRequest(email, password) {
	return cy
		.request({
			method: "POST",
			url: "/api/method/login",
			form: true,
			body: {
				usr: email,
				pwd: password,
			},
			failOnStatusCode: false,
		})
		.then((response) => {
			expect(response.status).to.eq(200);
		});
}

function loginWithSession(email, password) {
	return cy.session(
		["ifitwala-login", email],
		() => {
			loginViaRequest(email, password);
			validateLoggedInUser(email);
		},
		{
			validate: () => {
				validateLoggedInUser(email);
			},
		}
	);
}

function logout() {
	return cy
		.request({
			method: "GET",
			url: "/logout?redirect-to=%2Flogin",
			failOnStatusCode: false,
			followRedirect: false,
		})
		.then(() => {
			cy.clearCookies();
			cy.clearLocalStorage();
		});
}

module.exports = {
	e2eUsers,
	loginWithSession,
	logout,
	validateLoggedInUser,
};
