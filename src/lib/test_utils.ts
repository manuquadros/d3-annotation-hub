import { fireEvent } from "@testing-library/svelte";

class MockDataTransfer {
    data = {};

    setData(format: string, data: string) {
        this.data[format] = data;
    }

    getData(format: string) {
        return this.data[format];
    }

    clearData() {
        this.data = {};
    }
}

export async function dragAndDrop(
    user: UserEvent,
    source: Element,
    target: Element,
): Promise<void> {
    await user.pointer({ target: source, keys: "[MouseLeft>]" });

    const dataTransfer = new MockDataTransfer();

    fireEvent.dragStart(source, { dataTransfer });

    fireEvent.dragEnter(target);
    fireEvent.dragOver(target, { dataTransfer });

    fireEvent.drop(target, { dataTransfer });

    fireEvent.dragEnd(source);

    await user.pointer({ target: target, keys: "[/MouseLeft]" });
}
