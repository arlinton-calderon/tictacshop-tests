console.log(mdc);

const lists = Array.from(document.querySelectorAll('.mdc-list'));
lists.forEach(list => {
    list = mdc.list.MDCList.attachTo(list);
    list.listElements.map(listItem => mdc.ripple.MDCRipple.attachTo(listItem));
});