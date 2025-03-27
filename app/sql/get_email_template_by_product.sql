SELECT * from emailtemplates
    WHERE product = LOWER({{product}})
    AND name = {{template_name}}
;