/**
 *
 * $Id$
 */
package com.zipc.garden.model.fmc.validation;

/**
 * A sample validator interface for {@link com.zipc.garden.model.fmc.FMCNodePath}. This doesn't really do anything, and it's not
 * a real EMF artifact. It was generated by the org.eclipse.emf.examples.generator.validator plug-in to illustrate how EMF's
 * code generator can be extended. This can be disabled with -vmargs -Dorg.eclipse.emf.examples.generator.validator=false.
 */
public interface FMCNodePathValidator {
    boolean validate();

    boolean validateFullpath(String value);

    boolean validateSimplePath(String value);

    boolean validateNodeName(String value);
}
