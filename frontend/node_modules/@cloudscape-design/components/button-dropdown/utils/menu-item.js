/**
 * @returns attributes for a menuitem widget given parameters
 */
export const getMenuItemProps = ({ disabled, parent, expanded, }) => ({
    role: 'menuitem',
    'aria-disabled': disabled ? 'true' : undefined,
    'aria-haspopup': parent ? 'true' : undefined,
    'aria-expanded': expanded ? 'true' : parent ? 'false' : undefined,
});
export const getMenuItemCheckboxProps = ({ disabled, checked, }) => ({
    role: 'menuitemcheckbox',
    'aria-disabled': disabled ? 'true' : undefined,
    'aria-checked': checked ? 'true' : 'false',
});
//# sourceMappingURL=menu-item.js.map