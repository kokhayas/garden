/**
 *
 * $Id$
 */
package com.zipc.garden.model.scenario.validation;

import com.zipc.garden.model.scenario.ValueCondition;
import com.zipc.garden.model.scenario.Vehicle;

/**
 * A sample validator interface for {@link com.zipc.garden.model.scenario.RelativeSpeedCondition}.
 * This doesn't really do anything, and it's not a real EMF artifact.
 * It was generated by the org.eclipse.emf.examples.generator.validator plug-in to illustrate how EMF's code generator can be extended.
 * This can be disabled with -vmargs -Dorg.eclipse.emf.examples.generator.validator=false.
 */
public interface RelativeSpeedConditionValidator {
    boolean validate();

    boolean validateVehicle(Vehicle value);
    boolean validateKph(ValueCondition value);
}
