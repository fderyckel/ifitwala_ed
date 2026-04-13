function testIdSelector(testId) {
	return `[data-testid="${String(testId || "").trim()}"]`;
}

module.exports = {
	testIdSelector,
};
