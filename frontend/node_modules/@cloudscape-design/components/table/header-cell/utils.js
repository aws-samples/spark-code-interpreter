const stateToIcon = {
    sortable: 'caret-down',
    ascending: 'caret-up-filled',
    descending: 'caret-down-filled',
};
export const getSortingStatus = (sortable, sorted, descending, disabled) => {
    if (sorted) {
        if (descending) {
            return 'descending';
        }
        return 'ascending';
    }
    if (sortable && !disabled) {
        return 'sortable';
    }
    return undefined;
};
export const getSortingIconName = (sortingState) => stateToIcon[sortingState];
export const isSorted = (column, sortingColumn) => column === sortingColumn ||
    (column.sortingField !== undefined && column.sortingField === sortingColumn.sortingField) ||
    (column.sortingComparator !== undefined && column.sortingComparator === sortingColumn.sortingComparator);
export const getSortingColumnId = (columnDefinitions = [], sortingColumn) => {
    if (!sortingColumn) {
        return null;
    }
    for (let i = 0; i < columnDefinitions.length; i++) {
        if (isSorted(columnDefinitions[i], sortingColumn)) {
            return columnDefinitions[i].id || null;
        }
    }
    return null;
};
//# sourceMappingURL=utils.js.map