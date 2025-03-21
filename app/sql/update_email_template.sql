UPDATE emailtemplates
SET template = {{template}},
    subject = {{subject}}
WHERE product = {{product}}
AND id = {{template_id}}
;