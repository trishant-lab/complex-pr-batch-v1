SELECT * from email_templates
    WHERE product = (SELECT id FROM product WHERE name = {{product | lower}})
    AND name = {{template_name}}