// fixme: remove?
let Logic = (function createLogicFactory() {
  let logicPrototype = {
    getActionType: function() {
      return this.action_type;
    },

    getFieldName: function () {
        return `field_${this.field_id}`;
    }
  };

  return function(logic){
    let newLogic = Object.create(logicPrototype);
    Object.assign(newLogic, logic);
    return newLogic;
  }
})();

export function launch() {
    let rows = document.querySelectorAll('.form .field');
    if (rows.length > 1) {
        Array.from(rows).forEach(function (row) {
            let fieldLogicString = row.getAttribute('data-logic');
            if (fieldLogicString !== null) {
                let actions = JSON.parse(fieldLogicString);
                actions.forEach(function (logic) {
                    if (logic.action_type === "show") {
                        for (let rule of logic.rules) {
                            document.querySelectorAll(`input[name="field_${rule.field_name}"]`)
                                .forEach(input => input.addEventListener("change", function () {
                                    let selected;
                                    if (this.type === 'checkbox') {
                                        const inputs = document.querySelectorAll(inputSelector);
                                        selected = Array.from(inputs)
                                            .filter(i => i.checked)
                                            .map(i => i.value);
                                    } else {
                                        selected = [this.value];
                                    }
                                    const expected = new Set(
                                        rule.value.map(item => item.toString())
                                    );
                                    let intersection = new Set(
                                        [...selected].filter( i => expected.has(i))
                                    );
                                    if (intersection.size > 0) {
                                        row.classList.remove("hidden");
                                    } else {
                                        row.classList.add("hidden");
                                    }
                            }));
                        }
                    }
                })
            }

        });
    }
}
