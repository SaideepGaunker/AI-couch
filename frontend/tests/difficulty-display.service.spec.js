/**
 * Unit tests for DifficultyDisplayService - Frontend difficulty label consistency
 * Tests Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
 */

describe('DifficultyDisplayService', function() {
    'use strict';

    var DifficultyDisplayService;

    // Load the module
    beforeEach(module('interviewPrepApp'));

    // Inject the service
    beforeEach(inject(function(_DifficultyDisplayService_) {
        DifficultyDisplayService = _DifficultyDisplayService_;
    }));

    describe('getDifficultyLabel', function() {
        it('should return consistent labels for same internal levels', function() {
            var expectedMappings = {
                1: 'Easy',
                2: 'Medium',
                3: 'Hard',
                4: 'Expert'
            };

            for (var level in expectedMappings) {
                var actualLabel = DifficultyDisplayService.getDifficultyLabel(parseInt(level));
                expect(actualLabel).toBe(expectedMappings[level]);
            }
        });

        it('should return identical results for multiple calls with same input', function() {
            var levels = [1, 2, 3, 4];
            
            levels.forEach(function(level) {
                var firstCall = DifficultyDisplayService.getDifficultyLabel(level);
                var secondCall = DifficultyDisplayService.getDifficultyLabel(level);
                var thirdCall = DifficultyDisplayService.getDifficultyLabel(level);

                expect(firstCall).toBe(secondCall);
                expect(secondCall).toBe(thirdCall);
                expect(firstCall).toBe(thirdCall);
            });
        });

        it('should handle invalid inputs gracefully', function() {
            var invalidInputs = [0, 5, -1, 999, 'invalid', null, undefined];
            
            invalidInputs.forEach(function(input) {
                var result = DifficultyDisplayService.getDifficultyLabel(input);
                expect(result).toBe('Easy'); // Should default to Easy
            });
        });

        it('should handle string numbers correctly', function() {
            expect(DifficultyDisplayService.getDifficultyLabel('1')).toBe('Easy');
            expect(DifficultyDisplayService.getDifficultyLabel('2')).toBe('Medium');
            expect(DifficultyDisplayService.getDifficultyLabel('3')).toBe('Hard');
            expect(DifficultyDisplayService.getDifficultyLabel('4')).toBe('Expert');
        });
    });

    describe('getInternalLevel', function() {
        it('should correctly reverse getDifficultyLabel mappings', function() {
            var levels = [1, 2, 3, 4];
            
            levels.forEach(function(level) {
                var label = DifficultyDisplayService.getDifficultyLabel(level);
                var reverseLevel = DifficultyDisplayService.getInternalLevel(label);
                expect(reverseLevel).toBe(level);
            });
        });

        it('should be case insensitive', function() {
            var testCases = [
                { input: 'easy', expected: 1 },
                { input: 'EASY', expected: 1 },
                { input: 'Easy', expected: 1 },
                { input: 'medium', expected: 2 },
                { input: 'MEDIUM', expected: 2 },
                { input: 'Medium', expected: 2 },
                { input: 'hard', expected: 3 },
                { input: 'HARD', expected: 3 },
                { input: 'Hard', expected: 3 },
                { input: 'expert', expected: 4 },
                { input: 'EXPERT', expected: 4 },
                { input: 'Expert', expected: 4 }
            ];

            testCases.forEach(function(testCase) {
                var result = DifficultyDisplayService.getInternalLevel(testCase.input);
                expect(result).toBe(testCase.expected);
            });
        });

        it('should handle whitespace correctly', function() {
            expect(DifficultyDisplayService.getInternalLevel(' easy ')).toBe(1);
            expect(DifficultyDisplayService.getInternalLevel('  medium  ')).toBe(2);
            expect(DifficultyDisplayService.getInternalLevel('\thard\t')).toBe(3);
            expect(DifficultyDisplayService.getInternalLevel('\nexpert\n')).toBe(4);
        });

        it('should handle invalid inputs gracefully', function() {
            var invalidInputs = ['invalid', '', null, undefined, 123, []];
            
            invalidInputs.forEach(function(input) {
                var result = DifficultyDisplayService.getInternalLevel(input);
                expect(result).toBe(2); // Should default to Medium (level 2)
            });
        });
    });

    describe('getStringLevel', function() {
        it('should return correct string levels for internal levels', function() {
            var expectedMappings = {
                1: 'easy',
                2: 'medium',
                3: 'hard',
                4: 'expert'
            };

            for (var level in expectedMappings) {
                var result = DifficultyDisplayService.getStringLevel(parseInt(level));
                expect(result).toBe(expectedMappings[level]);
            }
        });

        it('should handle invalid inputs gracefully', function() {
            var invalidInputs = [0, 5, -1, 999, 'invalid', null, undefined];
            
            invalidInputs.forEach(function(input) {
                var result = DifficultyDisplayService.getStringLevel(input);
                expect(result).toBe('medium'); // Should default to medium
            });
        });
    });

    describe('normalizeDifficultyInput', function() {
        it('should handle various input types consistently', function() {
            var testCases = [
                { input: 1, expected: 1 },
                { input: '1', expected: 1 },
                { input: 'easy', expected: 1 },
                { input: 'Easy', expected: 1 },
                { input: 2, expected: 2 },
                { input: '2', expected: 2 },
                { input: 'medium', expected: 2 },
                { input: 'Medium', expected: 2 },
                { input: 3, expected: 3 },
                { input: '3', expected: 3 },
                { input: 'hard', expected: 3 },
                { input: 'Hard', expected: 3 },
                { input: 4, expected: 4 },
                { input: '4', expected: 4 },
                { input: 'expert', expected: 4 },
                { input: 'Expert', expected: 4 }
            ];

            testCases.forEach(function(testCase) {
                var result = DifficultyDisplayService.normalizeDifficultyInput(testCase.input);
                expect(result).toBe(testCase.expected);
            });
        });

        it('should handle invalid inputs gracefully', function() {
            var invalidInputs = [0, 5, -1, 'invalid', null, undefined];
            
            invalidInputs.forEach(function(input) {
                var result = DifficultyDisplayService.normalizeDifficultyInput(input);
                expect(result).toBe(2); // Should default to level 2
            });
        });
    });

    describe('updateDifficultyDisplay', function() {
        var testElement;

        beforeEach(function() {
            // Create a test element
            testElement = document.createElement('div');
            testElement.id = 'test-difficulty-display';
            document.body.appendChild(testElement);
        });

        afterEach(function() {
            // Clean up test element
            if (testElement && testElement.parentNode) {
                testElement.parentNode.removeChild(testElement);
            }
        });

        it('should update element text with correct difficulty label', function() {
            var testCases = [
                { input: 1, expectedText: 'Easy', expectedClass: 'difficulty-easy' },
                { input: 2, expectedText: 'Medium', expectedClass: 'difficulty-medium' },
                { input: 3, expectedText: 'Hard', expectedClass: 'difficulty-hard' },
                { input: 4, expectedText: 'Expert', expectedClass: 'difficulty-expert' }
            ];

            testCases.forEach(function(testCase) {
                DifficultyDisplayService.updateDifficultyDisplay('test-difficulty-display', testCase.input);
                
                expect(testElement.textContent).toBe(testCase.expectedText);
                expect(testElement.classList.contains(testCase.expectedClass)).toBe(true);
            });
        });

        it('should handle string inputs correctly', function() {
            DifficultyDisplayService.updateDifficultyDisplay('test-difficulty-display', 'medium');
            expect(testElement.textContent).toBe('Medium');
            expect(testElement.classList.contains('difficulty-medium')).toBe(true);
        });

        it('should handle non-existent element gracefully', function() {
            // Should not throw error for non-existent element
            expect(function() {
                DifficultyDisplayService.updateDifficultyDisplay('non-existent-element', 2);
            }).not.toThrow();
        });

        it('should replace existing difficulty classes', function() {
            // Set initial class
            testElement.classList.add('difficulty-easy');
            
            // Update to different difficulty
            DifficultyDisplayService.updateDifficultyDisplay('test-difficulty-display', 3);
            
            expect(testElement.classList.contains('difficulty-easy')).toBe(false);
            expect(testElement.classList.contains('difficulty-hard')).toBe(true);
        });
    });

    describe('getAllLevels', function() {
        it('should return all difficulty levels with correct mappings', function() {
            var allLevels = DifficultyDisplayService.getAllLevels();
            
            expect(allLevels).toBeDefined();
            expect(Object.keys(allLevels).length).toBe(4);
            
            var expectedLevels = {
                1: { display_label: 'Easy', string_level: 'easy' },
                2: { display_label: 'Medium', string_level: 'medium' },
                3: { display_label: 'Hard', string_level: 'hard' },
                4: { display_label: 'Expert', string_level: 'expert' }
            };

            for (var level in expectedLevels) {
                expect(allLevels[level]).toEqual(expectedLevels[level]);
            }
        });
    });

    describe('validateDifficultyConsistency', function() {
        it('should validate correct level-label combinations', function() {
            var validCases = [
                { level: 1, label: 'Easy' },
                { level: 1, label: 'easy' },
                { level: 1, label: 'EASY' },
                { level: 2, label: 'Medium' },
                { level: 2, label: 'medium' },
                { level: 2, label: 'MEDIUM' },
                { level: 3, label: 'Hard' },
                { level: 3, label: 'hard' },
                { level: 3, label: 'HARD' },
                { level: 4, label: 'Expert' },
                { level: 4, label: 'expert' },
                { level: 4, label: 'EXPERT' }
            ];

            validCases.forEach(function(testCase) {
                var result = DifficultyDisplayService.validateDifficultyConsistency(testCase.level, testCase.label);
                expect(result).toBe(true);
            });
        });

        it('should reject incorrect level-label combinations', function() {
            var invalidCases = [
                { level: 1, label: 'Medium' },
                { level: 2, label: 'Hard' },
                { level: 3, label: 'Expert' },
                { level: 4, label: 'Easy' },
                { level: 1, label: 'invalid' },
                { level: 2, label: '' },
                { level: 3, label: null }
            ];

            invalidCases.forEach(function(testCase) {
                var result = DifficultyDisplayService.validateDifficultyConsistency(testCase.level, testCase.label);
                expect(result).toBe(false);
            });
        });
    });

    describe('Backend-Frontend Consistency', function() {
        it('should use identical difficulty labels as backend', function() {
            // These should match the backend DifficultyMappingService.DIFFICULTY_LABELS
            var backendLabels = {
                1: 'Easy',
                2: 'Medium',
                3: 'Hard',
                4: 'Expert'
            };

            for (var level in backendLabels) {
                var frontendLabel = DifficultyDisplayService.getDifficultyLabel(parseInt(level));
                expect(frontendLabel).toBe(backendLabels[level]);
            }
        });

        it('should use identical string levels as backend', function() {
            // These should match the backend DifficultyMappingService.LEVEL_TO_STRING
            var backendStringLevels = {
                1: 'easy',
                2: 'medium',
                3: 'hard',
                4: 'expert'
            };

            for (var level in backendStringLevels) {
                var frontendStringLevel = DifficultyDisplayService.getStringLevel(parseInt(level));
                expect(frontendStringLevel).toBe(backendStringLevels[level]);
            }
        });
    });

    describe('Error Handling and Edge Cases', function() {
        it('should handle concurrent calls correctly', function() {
            // Simulate concurrent calls
            var results = [];
            for (var i = 0; i < 10; i++) {
                results.push(DifficultyDisplayService.getDifficultyLabel(2));
            }

            // All results should be identical
            results.forEach(function(result) {
                expect(result).toBe('Medium');
            });
        });

        it('should maintain consistency across service lifecycle', function() {
            // Test that service maintains consistency across multiple operations
            var level = 3;
            
            var label1 = DifficultyDisplayService.getDifficultyLabel(level);
            var internalLevel = DifficultyDisplayService.getInternalLevel(label1);
            var label2 = DifficultyDisplayService.getDifficultyLabel(internalLevel);
            var stringLevel = DifficultyDisplayService.getStringLevel(level);
            var normalizedLevel = DifficultyDisplayService.normalizeDifficultyInput(stringLevel);
            var label3 = DifficultyDisplayService.getDifficultyLabel(normalizedLevel);

            expect(label1).toBe(label2);
            expect(label2).toBe(label3);
            expect(internalLevel).toBe(level);
            expect(normalizedLevel).toBe(level);
        });
    });
});