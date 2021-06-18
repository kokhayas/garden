/**
 *
 * $Id$
 */
package com.zipc.garden.model.scenario.validation;

import com.zipc.garden.model.scenario.ComparisonOperator;

/**
 * A sample validator interface for {@link com.zipc.garden.model.scenario.SimpleValueCondition}.
 * This doesn't really do anything, and it's not a real EMF artifact.
 * It was generated by the org.eclipse.emf.examples.generator.validator plug-in to illustrate how EMF's code generator can be extended.
 * This can be disabled with -vmargs -Dorg.eclipse.emf.examples.generator.validator=false.
 */
public interface SimpleValueConditionValidator {
    boolean validate();

    boolean validateValue(double value);
    boolean validateOperator(ComparisonOperator value);
}
