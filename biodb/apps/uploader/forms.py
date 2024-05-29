from django import forms


class ModelForm(forms.ModelForm):
    def _post_clean(self, *args, **kwargs):
        """
        An internal hook for performing additional cleaning after form cleaning
        is complete. Used for model validation in model forms.

        The clean order is as:
        self._clean_fields()
        self._clean_form()
        self._post_clean() # <---- Model.clean() is called here.

        If errors already exist, report these to user rather than dealing with model errors that may not make sense
        when upstream field errors exist.
        """
        if self.errors:
            return
        return super()._post_clean(*args, **kwargs)
