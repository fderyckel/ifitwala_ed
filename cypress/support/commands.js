const { loginWithSession, logout, e2eUsers } = require("./auth");
const { testIdSelector } = require("./selectors");

function buildAppPath(prefix, path) {
	const normalizedPath = String(path || "").trim();
	if (!normalizedPath || normalizedPath === "/") {
		return prefix;
	}
	if (normalizedPath.startsWith(prefix)) {
		return normalizedPath;
	}
	if (normalizedPath.startsWith("/")) {
		return `${prefix}${normalizedPath}`;
	}
	return `${prefix}/${normalizedPath}`;
}

Cypress.Commands.add("getByTestId", (testId, ...args) => {
	return cy.get(testIdSelector(testId), ...args);
});

Cypress.Commands.add("loginWithSession", (email, password) => {
	return loginWithSession(email, password);
});

Cypress.Commands.add("loginAs", (alias) => {
	const user = e2eUsers[String(alias || "").trim()];
	if (!user) {
		throw new Error(`Unknown E2E user fixture: ${alias}`);
	}
	return loginWithSession(user.email, user.password);
});

Cypress.Commands.add("logout", () => {
	return logout();
});

Cypress.Commands.add("visitHub", (path = "/") => {
	return cy.visit(buildAppPath("/hub", path));
});

Cypress.Commands.add("visitAdmissions", (path = "/") => {
	return cy.visit(buildAppPath("/admissions", path));
});

Cypress.Commands.add("expectPath", (path) => {
	return cy.location("pathname").should("eq", path);
});
