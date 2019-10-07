import through2 from "through2";

export default function createEmptyStream() {
    var pass = through2.obj();
    process.nextTick(pass.end.bind(pass));
    return pass;
}