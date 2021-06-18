/**
 *
 * $Id$
 */
package com.zipc.garden.model.project.validation;

import com.zipc.garden.model.project.GPResource;

import org.eclipse.emf.common.util.EList;

/**
 * A sample validator interface for {@link com.zipc.garden.model.project.GPResource}. This doesn't really do anything, and it's
 * not a real EMF artifact. It was generated by the org.eclipse.emf.examples.generator.validator plug-in to illustrate how EMF's
 * code generator can be extended. This can be disabled with -vmargs -Dorg.eclipse.emf.examples.generator.validator=false.
 */
public interface GPResourceValidator {
    boolean validate();

    boolean validateParent(GPResource value);

    boolean validateChildren(EList<GPResource> value);

    boolean validateDirectory(boolean value);

    boolean validateName(String value);

    boolean validateId(long value);

    boolean validateId(int value);
}
