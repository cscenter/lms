export default function errorHandler(error) {
  const date = new Date();

  const now = date.toTimeString().split(" ")[0];

  const title = error.name + " in " + error.plugin;

  const message =
    "[" +
    now +
    "] " +
    [title.bold.red, "", error.message, ""].join("\n");

  // Print message to console
  // eslint-disable-next-line
  console.log(message);

  this.emit("end");
}